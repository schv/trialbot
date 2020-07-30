from aiogram import Bot, Dispatcher, executor, types
import face_recognition as fr
import ffmpeg
import os, shelve, urllib, wget
import numpy as np
from PIL import Image
from config import token
import logging

logging.basicConfig(level=logging.INFO)

base_path = '/home/ubunta/trialbot/trialbot'
os.chdir(base_path)
bot = Bot(token=token)
dp = Dispatcher(bot)
voices_shelf = shelve.open('voices', writeback=True)
faces_shelf = shelve.open('faces', writeback=True)

def make_unique_path(path):
    p, ext = os.path.splitext(path)
    path = next(
        new_path
        for i in range(10**6)
        if os.path.basename(new_path := f'{p}{i}{ext}') 
        not in os.listdir(os.path.dirname(path))
    )
    return path

@dp.message_handler(content_types=['photo'])
async def store_face(message: types.Message):
    best_img = max(message.photo, key=lambda p: p.file_size)
    user_id = str(message.from_user.id)

    image_file = await bot.get_file(best_img.file_id)
    url = f'https://api.telegram.org/file/bot{token}/{image_file.file_path}'

    with urllib.request.urlopen(url) as src:
        with Image.open(src as img:
            data = np.asarray(img)
            face = fr.face_locations(data)
            
            logging.log(level=logging.INFO, msg=f'Done looking for a face: {face}')
            if face:
                path = f'{base_path}/media/{image_file.file_path}'

                if os.path.exists(path):
                    path = make_unique_path(path)

                img.save(path)
                (
                    faces_shelf
                    .get(user_id, default=[])
                    .append((best_img.file_id, path))
                )


@dp.message_handler(content_types=['voice'])
async def store_voice(message: types.Message):
    voice_file = await bot.get_file(message.voice.file_id)
    user_id = str(message.from_user.id)
    
    url = f'https://api.telegram.org/file/bot{token}/{voice_file.file_path}'
    path = f'{base_path}/media/{voice_file.file_path}'.replace('.oga', '.wav')

    if os.path.exists(path):
        path = make_unique_path

    out, err = (
        ffmpeg
        .input(url)
        .output(path, ar=16000, loglevel='warning')
        .run()
    )
    
    logging.log(level=logging.INFO, msg=f'ffmpeg convertion completed')
    if out is not None:
        logging.log(level=logging.INFO, msg=f'ffmpeg output: {out}')
    if err is not None:
        logging.log(level=logging.ERROR, msg=f'ffmpeg output: {err}')
    
    (
        voices_shelf
        .get(user_id, default=[])
        .append((voice_file.file_id, path))
    )


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
