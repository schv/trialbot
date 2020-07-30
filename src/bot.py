import logging
import os
import shelve
import urllib
from pathlib import Path

import face_recognition as fr
import ffmpeg
import numpy as np
import wget
from aiogram import Bot, Dispatcher, executor, types
from PIL import Image

# config must be created before usage
from config import token

logging.basicConfig(level=logging.INFO)

base_path = Path(__file__).absolute().parent.parent
os.chdir(base_path)

bot = Bot(token=token)
dp = Dispatcher(bot)


def init_directories(base_path: Path):
    if not (media_path := base_path.joinpath('media')).exists():
        media_path.mkdir()

    if not (voice_path := media_path.joinpath('voice')).exists():
        voice_path.mkdir()

    if not (photos_path := media_path.joinpath('photos')).exists():
        photos_path.mkdir()


def make_unique_path(path: Path):
    directory, name, ext = path.parent, path.stem, path.suffix
    path = next(
        new_path
        for i in range(10**6)
        if (new_path := directory.joinpath(f'{name}{i}{ext}')).name
        not in os.listdir(path.parent)
    )
    return path


@dp.message_handler(content_types=['photo'])
async def store_face(message: types.Message):
    best_img = max(message.photo, key=lambda p: p.file_size)
    user_id = str(message.from_user.id)

    image_file = await bot.get_file(best_img.file_id)
    url = f'https://api.telegram.org/file/bot{token}/{image_file.file_path}'

    with urllib.request.urlopen(url) as src:
        with Image.open(src) as img:
            data = np.asarray(img)
            face = fr.face_locations(data)

            logging.log(
                level=logging.INFO,
                msg=f'Done looking for a face in {image_file.file_path}: {face}'
            )

            if face:
                path = base_path.joinpath('media', image_file.file_path)

                if path.exists():
                    path = make_unique_path(path)
                
                logging.log(
                    level=logging.INFO,
                    msg=f'Saving image into {path}'
                )

                img.save(path)
                with shelve.open('faces.dat', writeback=True) as faces_shelf:
                    (
                        faces_shelf
                        .get(user_id, default=[])
                        .append((best_img.file_id, str(path)))
                    )


@dp.message_handler(content_types=['voice'])
async def store_voice(message: types.Message):
    voice_file = await bot.get_file(message.voice.file_id)
    user_id = str(message.from_user.id)

    url = f'https://api.telegram.org/file/bot{token}/{voice_file.file_path}'
    path = base_path.joinpath(
        'media', voice_file.file_path.replace('.oga', '.wav'))

    if os.path.exists(path):
        path = make_unique_path(path)

    out, err = (
        ffmpeg
        .input(url)
        .output(str(path), ar=16000, loglevel='warning')
        .run()
    )

    logging.log(level=logging.INFO,
                msg=f'ffmpeg convertion completed for {voice_file.file_path}')

    if out is not None:
        logging.log(level=logging.INFO,
                    msg=f'ffmpeg output for {voice_file.file_path}: {out}')

    if err is not None:
        logging.log(level=logging.ERROR,
                    msg=f'ffmpeg error for {voice_file.file_path}: {err}')

    with shelve.open('voices.dat', writeback=True) as voices_shelf:
        (
            voices_shelf
            .get(user_id, default=[])
            .append((voice_file.file_id, str(path)))
        )


if __name__ == '__main__':
    init_directories(base_path)
    executor.start_polling(dp, skip_updates=True)
