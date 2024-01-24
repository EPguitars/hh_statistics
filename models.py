from dataclasses import dataclass, field
from typing import Optional

@dataclass
class VacancyRAW:
    
    # Название должности
    title: str
    # 5 типов зп: 
    # 1. По договоренности - "no numbers"
    # 2. Вилка "fork"
    # 3. Одно число "fixed"
    # 4. от "min"
    # 5. до "max"
    salary_type: str
    # Значение в поле для зарплаты в виде строки
    salary: str
    # Значение минимальной зп
    salary_min: int
    # Значение максимальной зп
    salary_max: int
    # url на страницу вакансии
    url: str
    # Город вакансии
    city: str
    # Требуемый опыт работы храним в словаре
    # [0] - без опыта
    # [5] - 5 лет
    # [1, 3] - от 1 до 3 лет
    experience: list
    # Если в карточке есть "Откликнитесь среди первых" - True, иначе False
    fresh: bool
    # Значит что вакансия актуальна и не в архиве
    is_actual: bool
    # Название компании
    company_name: str
    # url страницы компании
    company_page: str
    # Строка с помощью которой велся поиск
    search_strings: list
    # Дата когда соскребли данные
    when_scraped: str
    # Адрес компании
    company_address: str
    # Описание вакансии
    description: str
    # Тип занятости
    employment_type: str
    # айди вакансии
    source_id: str
    # Ключевые навыки, если нет то пустой сет
    key_skills: list
    # Спаршена ли страница вакансии
    is_scraped: bool
    # Находится ли страница вакансии в архиве
    is_archived: bool
    # Ответил ли я на вакансию
    responded: bool
    # Валюта зп
    salary_currency: str =  field(default=None)
    # айди от монго
    _id: str = field(default=None)

