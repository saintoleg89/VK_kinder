from random import randrange
import requests
from io import BytesIO


def upload_photo(upload, url):
    """
    Загрузка фотографии в оперативную память
    """
    img = requests.get(url).content
    f = BytesIO(img)

    response = upload.photo_messages(f)[0]

    owner_id = response['owner_id']
    photo_id = response['id']
    access_key = response['access_key']

    return owner_id, photo_id, access_key

def send_photo(vk, peer_id, owner_id, photo_id, access_key):
    """
    Отправка фотографии в чат
    """
    attachment = f'photo{owner_id}_{photo_id}_{access_key}'
    vk.messages.send(
        random_id=randrange(10 ** 7),
        chat_id=peer_id,
        attachment=attachment
    )
