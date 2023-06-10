import requests
import vk_api
from random import randrange
from vk_api import VkUpload
from vk_api.longpoll import VkLongPoll, VkEventType
from collections import Counter
from create_DataBase import Session, DatingUser, MatchingUser, Photos, BlacklistedUser, database_check
from settings import vk_token, search_token
from send_photo import upload_photo, send_photo


class VKinderBot:

    def __init__(self):
        """
        Запуск бота
        """
        print('Бот vkinder работает...')

    def start(self):
        """
        Установка соединения ВК
        """
        self.vk = vk_api.VkApi(token=vk_token)
        self.longpoll = VkLongPoll(self.vk)
        self.vk_up = self.vk.get_api()
        self.upload = VkUpload(self.vk_up)
        print('Соединение успешно установлено...')
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                if event.to_me:
                    if event.from_chat:
                        request = event.text.lower()
                        if request == 'привет':
                            self.say_hi(event)
                        elif request == 'пока':
                            self.say_bye(event)
                        elif request == 'vkinder':
                            self.vkinder_init_command(event)
                        else:
                            self.say_idk(event)

    def write_msg(self, user_id, message):
        """
        Отправка сообщений
        """
        self.vk.method('messages.send', {'chat_id': user_id, 'message': message, 'random_id': randrange(10 ** 7)})

    def say_hi(self, event):
        self.write_msg(event.chat_id, f'ПРИВЕТ, {event.user_id}...')
        self.say_idk(event)

    def say_bye(self, event):
        self.write_msg(event.chat_id, 'ПОКА...')

    def say_idk(self, event):
        """
        Ответ на любую неизвестную команду
        """
        self.write_msg(event.chat_id, 'СПИСОК КОМАНД:\n'
                                      '- ПРИВЕТ,\n'
                                      '- ПОКА,\n'
                                      '- VKINDER(ДЛЯ ЗАПУСКА БОТА)...')

    def wait_command(self):
        """
        Получение следующего ответа пользователя
        """
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                if event.to_me:
                    if event.from_chat:
                        request = event.text.lower()
                        return request

    def vkinder_init_command(self, event):
        """
        Корневой раздел сервиса знакомств
        """
        session = Session()
        dating_id = event.user_id
        user = session.query(DatingUser).filter(DatingUser.dating_id == dating_id).all()
        print('Проверка данных о пользователе в базе бота...')
        if len(user) == 0:
            self.add_new_dating_user(event)
            print('Пользователь не найден в базе бота...')
            return self.vkinder_init_command(event)
        else:
            self.write_msg(event.chat_id, f'Я ВИЖУ, ВЫ ЗДЕСЬ НЕ ВПЕРВЫЕ {event.user_id}, ЧТО БУДЕМ ДЕЛАТЬ?...')
            self.show_vkinder_commands(event)
            print('Пользователь найден в базе бота...')
            for event in self.longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW:
                    if event.to_me:
                        if event.from_chat:
                            request = event.text.lower()
                            if request == 'новые партнёры':
                                self.search_new_partners(event)
                            elif request == 'покажи понравившихся':
                                self.see_liked(event)
                            elif request == 'покажи чс':
                                self.see_blacklisted(event)
                            elif request == 'обнови информацию':
                                self.update_user_data(event)
                            elif request == 'удали понравившихся':
                                self.drop_liked(event)
                            elif request == 'удали чс':
                                self.drop_blacklisted(event)
                            elif request == 'удали пользователя':
                                self.drop_user_data(event)
                            elif request == 'в начало':
                                self.write_msg(event.chat_id, 'ВЫ ПЕРЕШЛИ В НАЧАЛО...')
                                return
                            else:
                                self.show_vkinder_commands(event)

    def search_new_partners(self, event):
        """
        Получение исходных данных для поиска партнёров
        """
        session = Session()
        id_dater = event.user_id
        user = session.query(DatingUser).filter(DatingUser.dating_id == id_dater).all()
        age_min = user[0].age_min
        age_max = user[0].age_max
        city_id = user[0].city_id
        offset = 0
        sex = user[0].partners_sex
        self.show_possible_partners(event, search_token, offset, city_id, sex, age_min, age_max)

    def show_possible_partners(self, event, search_token, offset, city_name, sex, age_min, age_max):
        """
        Отправка запроса для поиска новых партнёров
        """
        r = self.users_search_request(search_token, offset, city_name, sex, age_min, age_max)
        id_list = []
        for entry in r:
            if entry['is_closed'] == False:
                set_id = (entry['first_name'], entry['last_name'], entry['id'])
                id_list.append(set_id)
            else:
                continue
        for entry_id in id_list:
            check = database_check(entry_id[2])
            if check == True:
                continue
            else:
                pics = self.userpics_request(search_token, entry_id[2])
                pics_dict = {pic['sizes'][-1]['url']: pic['likes']['count'] for pic in pics}
                k = Counter(pics_dict)
                top3_pics = k.most_common(3)
                top3_pics_links = [pic[0] for pic in top3_pics]
                self.write_msg(event.chat_id, entry_id[0] + ' ' + entry_id[1])
                elm_link = 'https://vk.com/id' + str(entry_id[2])
                self.write_msg(event.chat_id, elm_link)
                for pic in top3_pics_links:
                    send_photo(self.vk_up, event.chat_id, *upload_photo(self.upload, pic))
                    self.write_msg(event.chat_id, pic)
                self.write_msg(event.chat_id, 'СПИСОК КОМАНД:\n'
                                              'YES - ДОБАВИТЬ В СПИСОК ПОНРАВИВШИХСЯ,\n'
                                              'NO - ДОБАВИТЬ В СПИСОК ЧС,\n'
                                              'STOP - ОСТАНОВИТЬ ПОИСК,\n'
                                              'ЛЮБОЕ СООБЩЕНИЕ ЧТОБЫ ПОКАЗАТЬ СЛЕДУЮЩЕГО...')
                request = self.wait_command()
                if request == 'yes':
                    self.add_liked(top3_pics, entry_id[2])
                    self.write_msg(event.chat_id, f'ПОЛЬЗОВАТЕЛЬ {entry_id} ЗАПИСАН В ПОНРАВИВШИХСЯ...')
                elif request == 'no':
                    self.add_blocked(entry_id)
                    self.write_msg(event.chat_id, f'ПОЛЬЗОВАТЕЛЬ {entry_id} ЗАПИСАН В ЧС...')
                elif request == 'stop':
                    self.show_vkinder_commands(event)
                    return
        self.write_msg(event.chat_id, 'СПИСОК ОКОНЧЕН, ЧТО ДАЛЬШЕ?\n'
                                      'СПИСОК КОМАНД:\n'
                                      '- ПОКАЖИ ПОНРАВИВШИХСЯ,\n'
                                      '- ПОКАЖИ ЧС,\n'
                                      '- NEXT,\n'
                                      '- ПЕРЕШЛИ В НАЧАЛО...')
        request = self.wait_command()
        request = request.lower()
        if request == 'next':
            offset += 20
            return self.show_possible_partners(event, search_token, offset, city_name, sex, age_min, age_max)
        elif request == 'покажи понравившихся':
            self.see_liked(event)
        elif request == 'покажи чс':
            self.see_blacklisted(event)
        else:
            self.write_msg(event.chat_id, 'ПЕРЕШЛИ В НАЧАЛО')
            return

    def userpics_request(self, search_token, elm_id):
        """
        Запрос информации о фотографиях пользователя
        """
        r = requests.get(
            'https://api.vk.com/method/photos.get',
            params={
                'access_token': {search_token},
                'v': 5.131,
                'owner_id': {elm_id},
                'album_id': 'profile',
                'rev': 0,
                'extended': 1,
                'photos_sizes': 'z'
            })
        return r.json()['response']['items']

    def users_search_request(self, search_token, offset, city_name, sex, age_min, age_max):
        """
         Запрос информации о пользователе
        """
        r = requests.get('https://api.vk.com/method/users.search',
                         params={
                             'access_token': {search_token},
                             'v': 5.131,
                             'sort': 0,
                             'offset': {offset},
                             'city': {city_name},
                             'has_photo': 1,
                             'sex': {sex},
                             'status': 6,
                             'age_from': {age_min},
                             'age_to': {age_max}
                         })
        r = r.json()['response']['items']
        return r

    def add_liked(self, top3_pics, matching_id):
        """
        Метод для записи в БД понравившихся пользователей
        """
        session = Session()
        user = session.query(DatingUser).all()
        id_dater = user[0].dating_id
        r = requests.get(
            'https://api.vk.com/method/users.get',
            params={'access_token': vk_token,
                    'v': 5.131,
                    'user_ids': matching_id,
                    'fields': 'bdate, sex',
                    'name_case': 'Nom'})
        r = r.json()
        first_name = r['response'][0]['first_name']
        last_name = r['response'][0]['last_name']
        try:
            bdate = r['response'][0]['bdate']
        except:
            bdate = 'NA'
        sex = r['response'][0]['sex']
        liked_user = MatchingUser(matching_id=matching_id, first_name=first_name, last_name=last_name, bdate=bdate,
                                  id_dater=id_dater, sex=sex)
        session.add(liked_user)
        session.commit()
        for photo in top3_pics:
            pic_link = photo[0]
            pic_likes = photo[1]
            photo = Photos(id_matcher=matching_id, photo_link=pic_link, likes_count=pic_likes)
            session.add(photo)
            session.commit()

    def add_blocked(self, entry_id):
        """
        Метод для записи в БД чёрного списка
        """
        session = Session()
        user = session.query(DatingUser).all()
        id_dater = user[0].dating_id
        blacklisted_id = entry_id[2]
        first_name = entry_id[0]
        last_name = entry_id[1]
        disliked_user = BlacklistedUser(blacklisted_id=blacklisted_id, first_name=first_name, last_name=last_name,
                                        id_dater=id_dater)
        session.add(disliked_user)
        session.commit()

    def see_liked(self, event):
        """
        Вывод из БД понравившихся
        """
        session = Session()
        id_dater = event.user_id
        liked_users = session.query(MatchingUser).filter(MatchingUser.id_dater == id_dater).all()
        if len(liked_users) == 0:
            self.write_msg(event.chat_id, 'СПИСОК ПОНРАВИВШИХСЯ ПУСТ...')
        else:
            for liked_user in liked_users:
                first_name = liked_user.first_name
                last_name = liked_user.last_name
                id_like = liked_user.matching_id
                user_info = first_name + ' ' + last_name + ' ' + 'https://vk.com/id' + str(id_like)
                self.write_msg(event.chat_id, user_info)
                photos = session.query(Photos).filter(Photos.id_matcher == id_like).all()
                for photo in photos:
                    if id_like == photo.id_matcher:
                        self.write_msg(event.chat_id, photo.photo_link)
        self.show_vkinder_commands(event)

    def see_blacklisted(self, event):
        """
        Вывод из БД чёрного списка
        """
        session = Session()
        id_dater = event.user_id
        blacklisted_users = session.query(BlacklistedUser).filter(BlacklistedUser.id_dater == id_dater).all()
        if len(blacklisted_users) == 0:
            self.write_msg(event.chat_id, 'СПИСОК ЧС ПУСТ...')
        else:
            for user in blacklisted_users:
                first_name = user.first_name
                last_name = user.last_name
                id_black = user.blacklisted_id
                bl_user = first_name + ' ' + last_name + ' ' + 'https://vk.com/id' + str(id_black)
                self.write_msg(event.chat_id, bl_user)
        self.show_vkinder_commands(event)

    def update_user_data(self, event):
        """
        Обновление информации поиска
        """
        session = Session()
        user = session.query(DatingUser).all()[0]
        id_update = user.dating_id
        self.write_msg(event.chat_id, f'- УКАЖИТЕ МИНИМАЛЬНЫЙ ВОЗРАСТ ПОИСКА ПАРТНЁРОВ...')
        try:
            age_min = int(self.wait_command())
            if age_min < 18:
                self.write_msg(event.chat_id, f'АЙ, КАК НЕКРАСИВО...ВВЕДИТЕ МИНИМАЛЬНЫЙ ВОЗРАСТ БОЛЬШЕ 18 ЛЕТ...')
                return self.update_user_data(event)
        except:
            self.write_msg(event.chat_id, f'НИЧЕГО НЕ ПОНЯТНО, СПРОШУ ЕЩЁ РАЗ...')
            return self.update_user_data(event)
        self.write_msg(event.chat_id, f'- УКАЖИТЕ МАКСИМАЛЬНЫЙ ВОЗРАСТ ПОИСКА ПАРТНЁРОВ...')
        try:
            age_max = int(self.wait_command())
            if age_max < 18:
                age_max = 18
        except:
            self.write_msg(event.chat_id, f'НИЧЕГО НЕ ПОНЯТНО, СПРОШУ ЕЩЁ РАЗ...')
            return self.update_user_data(event)
        self.write_msg(event.chat_id, f'- УКАЖИТЕ ПОЛ ПАРТНЁРОВ ДЛЯ ПОИСКА, М ИЛИ Ж...')
        partners_sex = self.wait_command()
        partners_sex = partners_sex.lower()
        if partners_sex == 'м':
            partners_sex = 2
        elif partners_sex == 'ж':
            partners_sex = 1
        else:
            self.write_msg(event.chat_id, f'НИЧЕГО НЕ ПОНЯТНО, СПРОШУ ЕЩЁ РАЗ...')
            return self.update_user_data(event)
        session.query(DatingUser).filter(DatingUser.dating_id == id_update).update(
            {'age_min': age_min, 'age_max': age_max, 'partners_sex': partners_sex})
        session.commit()
        self.write_msg(event.chat_id, 'ИНФОРМАЦИЯ ОБНОВЛЕНА...')

    def show_vkinder_commands(self, event):
        """
        Показать список доступных команд
        """
        self.write_msg(event.chat_id, 'СПИСОК ДОСТУПНЫХ КОМАНД:\n'
                                      '- НОВЫЕ ПАРТНЁРЫ\n'
                                      '- ПОКАЖИ ПОНРАВИВШИХСЯ\n'
                                      '- ПОКАЖИ ЧС\n'
                                      '- ОБНОВИ ИНФОРМАЦИЮ\n'
                                      '- УДАЛИ ПОНРАВИВШИХСЯ\n'
                                      '- УДАЛИ ЧС\n'
                                      '- В НАЧАЛО...')

    def add_new_dating_user(self, event):
        """
        Добавление нового пользователя
        """
        session = Session()
        self.write_msg(event.chat_id, 'НЕОБХОДИМО ВВЕСТИ ДАННЫЕ ДЛЯ РАБОТЫ БОТА VKINDER: ')
        vk_id = event.user_id
        r = requests.get('https://api.vk.com/method/users.get',
                         params={
                             'access_token': vk_token,
                             'v': 5.131,
                             'user_ids': vk_id,
                             'fields': 'bdate, sex, city',
                             'name_case': 'Nom'})
        r = r.json()
        print('Получены данные пользователя с сервера ВК...')
        try:
            first_name = r['response'][0]['first_name']
        except:
            self.write_msg(event.chat_id, 'ДАННЫХ ВАШЕЙ СТРАНИЦЫ ВК НЕДОСТАТОЧНО...')
            self.write_msg(event.chat_id, f'УКАЖИТЕ ВАШЕ ИМЯ...')
            first_name = self.wait_command()
        try:
            last_name = r['response'][0]['last_name']
        except:
            self.write_msg(event.chat_id, 'ДАННЫХ ВАШЕЙ СТРАНИЦЫ ВК НЕДОСТАТОЧНО...')
            self.write_msg(event.chat_id, f'УКАЖИТЕ ВАШУ ФАМИЛИЮ...')
            last_name = self.wait_command()
        try:
            city_name = r['response'][0]['city']['title']
        except:
            self.write_msg(event.chat_id, 'ДАННЫХ ВАШЕЙ СТРАНИЦЫ ВК НЕДОСТАТОЧНО...')
            self.write_msg(event.chat_id, f'УКАЖИТЕ ВАШ ГОРОД...')
            city_name = self.wait_command()
        try:
            city_id = r['response'][0]['city']['id']
        except:
            city_id = 'Неизвестно'
        try:
            bdate = r['response'][0]['bdate']
        except:
            self.write_msg(event.chat_id, 'ДАННЫХ ВАШЕЙ СТРАНИЦЫ ВК НЕДОСТАТОЧНО...')
            self.write_msg(event.chat_id, f'УКАЖИТЕ ВАШУ ДАТУ РОЖДЕНИЯ(НАПРИМЕР 01.01.1901)...')
            bdate = self.wait_command()
        try:
            sex = r['response'][0]['sex']
        except:
            self.write_msg(event.chat_id, 'ДАННЫХ ВАШЕЙ СТРАНИЦЫ ВК НЕДОСТАТОЧНО...')
            self.write_msg(event.chat_id, f'УКАЖИТЕ ВАШ ПОЛ...')
            sex = self.wait_command().lower
            if sex == 'м':
                sex = 2
            elif sex == 'ж':
                sex = 1
            else:
                self.write_msg(event.chat_id, f'Странно...')
                sex = 0
        self.write_msg(event.chat_id, f'УКАЖИТЕ МИНИМАЛЬНЫЙ ВОЗРАСТ ДЛЯ ПОИСКА ПАРТНЁРОВ...')
        try:
            age_min = int(self.wait_command())
            if age_min < 18:
                self.write_msg(event.chat_id, f'АЙ, КАК НЕКРАСИВО...ВВЕДИТЕ МИНИМАЛЬНЫЙ ВОЗРАСТ БОЛЬШЕ 18 ЛЕТ...')
                return self.add_new_dating_user(event)
        except:
            self.write_msg(event.chat_id, f'НИЧЕГО НЕ ПОНЯТНО, СПРОШУ ЕЩЁ РАЗ...')
            return self.add_new_dating_user(event)
        self.write_msg(event.chat_id, f'УКАЖИТЕ МАКСИМАЛЬНЫЙ ВОЗРАСТ ДЛЯ ПОИСКА ПАРТНЁРОВ...')
        try:
            age_max = int(self.wait_command())
            if age_max < 18:
                age_max = 18
        except:
            self.write_msg(event.chat_id, f'НИЧЕГО НЕ ПОНЯТНО, СПРОШУ ЕЩЁ РАЗ...')
            return self.add_new_dating_user(event)
        self.write_msg(event.chat_id, f'УКАЖИТЕ ПОЛ ПАРТНЁРОВ ДЛЯ ПОИСКА, М ИЛИ Ж...')
        partners_sex = self.wait_command()
        partners_sex = partners_sex.lower()
        if partners_sex == 'м':
            partners_sex = 2
        elif partners_sex == 'ж':
            partners_sex = 1
        else:
            self.write_msg(event.chat_id, f'НИЧЕГО НЕ ПОНЯТНО, СПРОШУ ЕЩЁ РАЗ...')
            return self.add_new_dating_user(event)
        user = DatingUser(dating_id=vk_id, first_name=first_name, last_name=last_name, city_name=city_name,
                          city_id=city_id, bdate=bdate,
                          age_min=age_min, age_max=age_max, sex=sex, partners_sex=partners_sex)
        session.add(user)
        session.commit()
        self.write_msg(event.chat_id, f'ПОЛЬЗОВАТЕЛЬ {vk_id} ДОБАВЛЕН В БАЗУ...')

    def drop_liked(self, event):
        """
        Удаление списка понравившихся из базы
        """
        session = Session()
        id_dater = event.user_id
        liked_users = session.query(MatchingUser).filter(MatchingUser.id_dater == id_dater).all()
        for liked_user in liked_users:
            id_matcher = liked_user.matching_id
            session.query(Photos).filter(Photos.id_matcher == id_matcher).delete()
            session.commit()
        session.query(MatchingUser).filter(MatchingUser.id_dater == id_dater).delete()
        session.commit()
        print('Таблица понравившихся в базе очищена...')
        self.write_msg(event.chat_id, 'СПИСОК ПОНРАВИВШИХСЯ ОЧИЩЕН...')
        self.show_vkinder_commands(event)

    def drop_blacklisted(self, event):
        """
        Удаление черного списка из базы
        """
        session = Session()
        id_dater = event.user_id
        session.query(BlacklistedUser).filter(BlacklistedUser.id_dater == id_dater).delete()
        session.commit()
        print('Таблица чс в базе очищена...')
        self.write_msg(event.chat_id, 'СПИСОК ЧС ОЧИЩЕН...')
        self.show_vkinder_commands(event)

    def drop_user_data(self, event):
        """
        Удаление данных о пользователе в базе
        """
        self.write_msg(event.chat_id, 'ВЫ УВЕРЕНЫ(ДА ИЛИ ...)?')
        reply = self.wait_command()
        reply = reply.lower()
        if reply == 'да':
            session = Session()
            self.drop_blacklisted(event)
            self.drop_liked(event)
            dating_id = event.user_id
            session.query(DatingUser).filter(DatingUser.dating_id == dating_id).delete()
            session.commit()
            self.write_msg(event.chat_id, 'ДАННЫЕ УДАЛЕНЫ...')
        else:
            self.write_msg(event.chat_id, 'НУ И ХОРОШО...')
