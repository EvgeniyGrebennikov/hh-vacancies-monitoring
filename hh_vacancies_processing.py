import pandas as pd
import requests
import json
import time
import os
import re
import configparser

# Указываем текущий путь
dirname = os.path.dirname(__file__)

# Считываем файл config.ini
config = configparser.ConfigParser()
config.read(os.path.join(dirname, 'config.ini'), encoding='utf-8')

file_name = config['FilePath']['file']

# Считываем список регионов, по которым нужны вакансии
cities = eval(config['Required_Vacancy']['regions'])
skills = eval(config['Required_Vacancy']['skills'])


# Функция считывания минус-фраз из файла (удаление отступов и приведение к нижнему регистру)
def load_negative_keywords(file_name):
    ser = pd.read_excel(file_name, header=None)
    ser.columns = ['words']
    ser = ser.map(lambda word: word.strip().lower())

    return sorted(ser['words'].unique().tolist())


# Функция на получение списка вакансий постранично
def getPage(current_name, page=0):

    # Справочник для параметров GET-запроса
    params = {
        'text': f'NAME:{current_name}',  # Текст фильтра. В имени должно быть слово "Аналитик"
        'area': 1,  # Поиск ощуществляется по вакансиям города Москва
        'page': page,  # Индекс страницы поиска на HH
        'per_page': 100  # Кол-во вакансий на 1 странице
    }

    req = requests.get('https://api.hh.ru/vacancies', params)  # Посылаем запрос к API
    data = req.content.decode()  # Декодируем ответ, чтобы Кириллица отображалась корректно
    req.close()
    return data


# Функция проверки вакансии на соответствие: название, скиллы, опыт, регион
def check_vacancy(vacancy, cities, negative_phrases_list):
    try:

        # Название вакансии подходит под условие - выводит True
        is_required_name = not(any(map(lambda name: name.lower() in vacancy.get('name').lower(), negative_phrases_list)))
        # Вакансия открыта - выводит True
        is_actual_vacancy = vacancy.get('type', {}).get('name') == 'Открытая'
        # Опыт работы совпадает с требуемым - выводит True
        is_required_experience = vacancy.get('experience').get('name') in ['Нет опыта', 'От 1 года до 3 лет']
        # Регион вакансии совпадает с требуемым - выводит True
        is_required_city = any(map(lambda city: city.lower() in str(vacancy).lower(), cities))
        # Наличие списка навыков skills в вакансии
        description = f"{vacancy.get('snippet').get('requirement')} {vacancy.get('snippet').get('responsibility')}".lower()
        is_required_skills = any(map(lambda skill: skill.strip().lower() in description, skills))

        return all([is_required_name, is_actual_vacancy, is_required_experience, is_required_city, is_required_skills])

    except Exception as err:
        print(f"Ошибка при проверке вакансии: {repr(err)}")


def extract_vacancies():
    # Создаем словарь для последующей записи вакансий
    vacancies_dict = {}

    # Пробегаемся по списку с названиями профессий, считываем по-странично вакансии
    for current_name in names:
        for page in range(0, 1): # Поменять 1 на 2000
            try:
                vacancies_obj = json.loads(getPage(current_name, page))
                vacancies_info = vacancies_obj.get('items')

                for vacancy in vacancies_info:
                    if check_vacancy(vacancy, cities, negative_phrases_list):
                        (id, name, has_test, address, salary, type_vacancy,
                         published_at, response_url, vacancy_url, company,
                         company_url, schedule, professional_roles, experience)  = [
                            vacancy.get('id'), vacancy.get('name'), vacancy.get('has_test'),
                            vacancy.get('address'), vacancy.get('salary'), vacancy.get('type').get('name'),
                            vacancy.get('published_at'), vacancy.get('apply_alternate_url'), vacancy.get('alternate_url'),
                            vacancy.get('employer').get('name'), vacancy.get('employer').get('alternate_url'),
                            vacancy.get('schedule').get('name'), vacancy.get('professional_roles'), vacancy.get('experience')
                        ]

                        vacancies_dict[id] = [name, has_test, address, salary, type_vacancy,
                         published_at, response_url, vacancy_url, company,
                         company_url, schedule, professional_roles, experience]

            except Exception as err:
                print(f"Ошибка при выгрузке данных: {repr(err)}\n{vacancies_obj}")

            if vacancies_obj['pages'] - page <= 1:
                break

    return vacancies_dict