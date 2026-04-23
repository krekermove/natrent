from django.shortcuts import render
from django.views import View

from .models import TimeTable


# Create your views here.

class MainView(View):
    def date_transform(self, date):
        return '-'.join(reversed(date.split('.')))

    def get(self, request):
        return render(request, 'main/index2.html')

    def post(self, request):
        first_date = self.date_transform(request.POST.get('firstInputDate'))
        second_date = self.date_transform(request.POST.get('secondInputDate'))
        guest_count = request.POST.get('guestInputValue')
        date_input_error = 'Вы не полностью выбрали даты проживания'
        print(first_date + "\n" + second_date + "\n" + guest_count)
        if not first_date or not second_date:
            context = {
                'date_input_error': date_input_error,
            }
            return render(request, template_name='main/index2.html', context=context)
        free_houses = TimeTable.objects.filter(startdate=first_date)
        print(free_houses[0].house)
        return render(request, 'main/index2.html')


def popular_list(request):
    return render(request,'main/index2.html')


class SearchView(View):
    pass