"""Створює демо-клас для презентації: python seed_demo.py
(пароль демо-вчителя береться з DEMO_PASSWORD або генерується й виводиться в консоль)"""
import os

from main import app
from teacher_platform import seed_demo

seed_demo(app, password=os.environ.get("DEMO_PASSWORD"))
