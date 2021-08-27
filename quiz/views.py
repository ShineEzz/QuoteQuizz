from django.shortcuts import render, redirect
from .forms import NewUserForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
import random
import distutils
from distutils import util
from django.db.models import Q
from django.template.defaulttags import register

from .models import Category, QuestionSet, Question, UsersQuestions, Quote


def homepage(request):
    categories = Category.objects.order_by('id').all()
    return render(request=request, template_name="quiz/homepage.html", context={'categories': categories})


def register_request(request):
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect("quiz:homepage")
        messages.error(request, "Unsuccessful registration. Invalid information.", extra_tags="danger")
    form = NewUserForm()
    return render(request=request, template_name="quiz/register.html", context={"register_form": form})


def login_request(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")
                return redirect("quiz:homepage")
            else:
                messages.error(request, "Invalid username or password.", extra_tags="danger")
        else:
            messages.error(request, "Invalid username or password.", extra_tags="danger")
    form = AuthenticationForm()
    return render(request=request, template_name="quiz/login.html", context={"login_form": form})


def logout_request(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("quiz:homepage")


def show_category(request, id):
    # category = Category.objects.filter(id=id)
    question_sets = QuestionSet.objects.filter(category_id=id)
    return render(request=request, template_name="quiz/category.html", context={"question_sets": question_sets, "category_id": id})


def category_next_question(request, id):
    category = Category.objects.get(pk=id)
    question_list = []

    if request.user.__class__.__name__ == 'AnonymousUser':
        answered_questions_list = []
    else:
        answered_questions_list = UsersQuestions.objects.filter(user=request.user).values_list('question_id')

    for qs in category.question_sets.all():
        question_list += qs.questions.filter(~Q(pk__in=answered_questions_list)).values_list('pk')

    question = Question.objects.filter(~Q(pk__in=answered_questions_list)).get(pk=random.choice(question_list)[0])
    return render(request=request, template_name="quiz/question.html", context={"question": question, "category": category})


def profile(request):
    users_questions = UsersQuestions.objects.filter(user_id=request.user.id)
    category_stats = {}
    for uq in users_questions:
        category = uq.question.quote_id.source.category_id
        category_stats[category.name] = category_stats.get(category.name, {'correct': 0, 'incorrect': 0})

        question_sets_pks = category.question_sets.values_list('pk', flat=True)
        all_questions_in_category = Question.objects.filter(question_set_id__in=question_sets_pks).count()
        category_stats[category.name]['all'] = category_stats[category.name].get('all', all_questions_in_category)
        category_stats[category.name]['all_percent'] = category_stats[category.name].get('all_percent', 100)

        if uq.is_correct:
            category_stats[category.name]['correct'] = category_stats[category.name].get('correct', 0) + 1
        else:
            category_stats[category.name]['incorrect'] = category_stats[category.name].get('incorrect', 0) + 1

    for key in category_stats:
        category_stats.get(key)['all_percent'] = round(category_stats.get(key).get('all_percent', 100), 1)
        category_stats.get(key)['correct_percent'] = round(category_stats.get(key).get('correct', 1) / category_stats.get(key).get('all') * 100, 1)
        category_stats.get(key)['incorrect_percent'] = round(category_stats.get(key).get('incorrect', 1) / category_stats.get(key).get('all') * 100, 1)
        category_stats.get(key)['remains'] = round(category_stats.get(key).get('all') - category_stats.get(key)['incorrect'] - category_stats.get(key)['correct'], 1)
        category_stats.get(key)['remains_percent'] = round(category_stats.get(key).get('all_percent') - category_stats.get(key)['incorrect_percent'] - category_stats.get(key)['correct_percent'], 1)

    return render(request=request, template_name="quiz/profile.html",
                  context={"category_stats": category_stats})


def answer(request):
    question = Question.objects.get(pk=request.POST['question_id'])
    boolean_value = bool(distutils.util.strtobool(request.POST['is_correct']))
    users_questions = UsersQuestions(question=question, user=request.user, is_correct=boolean_value)
    users_questions.save()

    response = {'saved': True}
    return JsonResponse(response)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

