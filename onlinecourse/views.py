from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import Course, Enrollment, Question, Choice, Submission


def index(request):
    courses = Course.objects.all()
    return render(request, 'onlinecourse/index.html', {'courses': courses})


def course_details(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    return render(request, 'onlinecourse/course_details_bootstrap.html', {'course': course})


@login_required
def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    enrollment, created = Enrollment.objects.get_or_create(
        user=request.user, course=course
    )
    if created:
        course.total_enrollment += 1
        course.save()
    return HttpResponseRedirect(reverse('onlinecourse:course_details', args=[course_id]))


@login_required
def submit(request, course_id):
    """Handle exam submission: create a Submission and link selected choices."""
    course = get_object_or_404(Course, pk=course_id)
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)

    submission = Submission.objects.create(enrollment=enrollment)

    # Collect all selected choice ids from POST data
    submitted_ids = []
    for key, values in request.POST.lists():
        if key.startswith('choice'):
            submitted_ids += [int(v) for v in values]

    selected_choices = Choice.objects.filter(id__in=submitted_ids)
    submission.choices.set(selected_choices)
    submission.save()

    return HttpResponseRedirect(
        reverse('onlinecourse:show_exam_result', args=[course_id, submission.id])
    )


@login_required
def show_exam_result(request, course_id, submission_id):
    """Evaluate the submission and render the result page."""
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    selected_ids = list(submission.choices.values_list('id', flat=True))

    total_score = 0
    results = []

    for question in course.questions.all():
        # Get the ids the user selected for this specific question
        user_selected = [
            cid for cid in selected_ids
            if Choice.objects.filter(id=cid, question=question).exists()
        ]
        correct = question.is_correct(user_selected)
        if correct:
            total_score += question.grade

        results.append({
            'question': question,
            'correct': correct,
            'selected_choices': submission.choices.filter(question=question),
        })

    max_score = sum(q.grade for q in course.questions.all())
    passed = total_score >= (max_score * 0.8) if max_score > 0 else False

    context = {
        'course': course,
        'submission': submission,
        'results': results,
        'total_score': total_score,
        'max_score': max_score,
        'passed': passed,
    }
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
