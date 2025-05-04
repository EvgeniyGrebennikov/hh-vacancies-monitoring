import pandas as pd
import numpy as np
import json
import os
import configparser
from hh_vacancies_processing import load_negative_keywords, getPage, check_vacancy

# Задаем настройку отображения кол-ва столбцов в датафрейме
pd.set_option('display.max_columns', 40)

# Указываем текущий путь
dirname = os.path.dirname(__file__)

# Считываем файл config.ini
config = configparser.ConfigParser()
config.read(os.path.join(dirname, 'config.ini'), encoding='utf-8')


# Считываем название файла vacancies.xlsx (для последующей записи вакансий)
res_vacancies_file = config['FilePath']['vacancies_file']

# Проверка на наличие файла vacancies.xlsx (записываем итоговые вакансии). Если файла нет - создаем
if not os.path.exists(res_vacancies_file):
    column_name = """id name has_test address salary type_vacancy 
    published_at response_url vacancy_url company 
                         company_url schedule professional_roles experience is_grequest comments""".split()
    vacancies_df = pd.DataFrame(columns=column_name)
    vacancies_df.to_excel(res_vacancies_file, index=False)


# Считываем файл с минус-фразами из назаний вакансий (отсекаем ненужные вакансии по этим фразам)
file_minus_phrases = config['FilePath']['file']
negative_phrases_list = load_negative_keywords(file_minus_phrases)

# Указываем названия профессий, по которым извлекаем вакансии hh
names = eval(config['Required_Vacancy']['vacancy_names'])
# Считываем список регионов, по которым нужны вакансии
cities = eval(config['Required_Vacancy']['regions'])
# Считываем список навыков
skills = eval(config['Required_Vacancy']['skills'])

# Создаем словарь для последующей записи вакансий
result_vacancies_dict = {}

# Пробегаемся по списку с названиями профессий, считываем по-странично вакансии
for current_name in names:
    for page in range(0, 2000): # Поменять 1 на 2000
        try:
            vacancies_obj = json.loads(getPage(current_name, page))
            vacancies_info = vacancies_obj.get('items')

            for vacancy in vacancies_info:
                if check_vacancy(vacancy, cities, negative_phrases_list):
                    (id, name, has_test, address, salary, type_vacancy,
                     published_at, response_url, vacancy_url, company,
                     company_url, schedule, professional_roles, experience,
                     is_request, comments)  = [
                        vacancy.get('id'), vacancy.get('name'), vacancy.get('has_test'),
                        vacancy.get('address')['city'] if vacancy.get('address') is not None else None, f"{vacancy.get('salary')['from']} - {vacancy.get('salary')['to']}" if vacancy.get('salary') is not None else None, vacancy.get('type').get('name'),
                        vacancy.get('published_at'), vacancy.get('apply_alternate_url'), vacancy.get('alternate_url'),
                        vacancy.get('employer').get('name'), vacancy.get('employer').get('alternate_url'),
                        vacancy.get('schedule').get('name'), vacancy.get('professional_roles')[0].get('name'), vacancy.get('experience').get('name'), np.nan, np.nan
                    ]

                    result_vacancies_dict[id] = [name, has_test, address, salary, type_vacancy,
                                                 published_at, response_url, vacancy_url, company, company_url,
                                                 schedule, professional_roles, experience, is_request, comments]

        except Exception as err:
            print(f"Ошибка при выгрузке данных: {repr(err)}\n{vacancies_obj}")

        if vacancies_obj['pages'] - page <= 1:
            break


# Преобразуем словарь выгруженных вакансий в датафрейм
new_vacancies_df = pd.DataFrame(result_vacancies_dict).T.reset_index()
column_name = """id name has_test address salary type_vacancy 
published_at response_url vacancy_url company 
                     company_url schedule professional_roles experience is_grequest comments""".split()

# Задаем названия столбцов для датафрейма (с новыми вакансиями)
new_vacancies_df.columns = column_name
new_vacancies_df['id'] = new_vacancies_df['id'].astype('int64')

# Считываем список прошых вакансий из файла (ранние выгрузки)
past_vacancies_df = pd.read_excel('vacancies.xlsx')
past_vacancies_df['id'] = past_vacancies_df['id'].astype('int64')

# Сопоставляем новые вакансии (по id) с информацией по ранними вакансиям, оставляем из новых вакансий только уникальные
actual_vacancies_df = new_vacancies_df[~new_vacancies_df['id'].isin(past_vacancies_df['id'].tolist())]

# Объединяем прошлые вакансии с новыми актуальными
df = pd.concat([past_vacancies_df, actual_vacancies_df])

# Сортируем итоговый датафрейм по дате публикации (от новых к старым)
df.sort_values(['published_at', 'name', 'vacancy_url'], ascending=[False, True, True], inplace=True)

df.to_excel('vacancies.xlsx', index=False)
print('Загрузка завершена')
