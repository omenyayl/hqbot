import os
import time
from pprint import pprint
import json

import cv2
import pandas as pd
import pytesseract
from nltk.stem.porter import *
from nltk.tokenize import word_tokenize

from async_requests import google_search

SCREENSHOTS_PATH = os.path.join(os.path.dirname(__file__), "screenshots")
SCREENSHOT_PATH = os.path.join(SCREENSHOTS_PATH, 'screen.png')
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")


def main():
    parse_config()
    print('Starting ADB server...')
    os.system('adb start-server')
    while True:
        user_input = None
        try:
            user_input = show_prompt()
        except ValueError:
            print('Your selection is not a number!')

        if user_input == 0:
            break
        if user_input == 1:
            run()
        else:
            print('Not a valid option!')


def take_screenshot(screenshot_path):
    if os.path.exists(screenshot_path):
        os.remove(screenshot_path)
    os.system('adb exec-out screencap -p > {}'.format(screenshot_path))


def get_question_text(screenshot_path):
    img = cv2.imread(screenshot_path)
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = img_gray.shape
    img_gray = img_gray[:, int(0.8 / 9 * width):1 - int(0.8 / 9 * width)]  # removes border from the left and right side
    question_img = img_gray[int(1.8 / 9 * height):int(3.2 / 9 * height), :]
    option1_img = img_gray[int(3.5 / 9 * height):int(4.3 / 9 * height), :]
    option2_img = img_gray[int(4.3 / 9 * height):int(5.05 / 9 * height), :]
    option3_img = img_gray[int(5.05 / 9 * height):int(5.85 / 9 * height), :]
    question_text = pytesseract.image_to_string(question_img).replace('\n', ' ')
    option1_text = pytesseract.image_to_string(option1_img)
    option2_text = pytesseract.image_to_string(option2_img)
    option3_text = pytesseract.image_to_string(option3_img)
    return {
        'question': question_text,
        'options': [
            option1_text, option2_text, option3_text
        ]
    }


def run():
    if not os.path.exists(SCREENSHOTS_PATH):
        os.mkdir(SCREENSHOTS_PATH)
    tic = time.time()
    take_screenshot(SCREENSHOT_PATH)

    question_with_options = get_question_text(SCREENSHOT_PATH)
    question = question_with_options['question']
    options = question_with_options['options']

    what_to_google = '{} AND "{}" OR "{}" OR "{}"'.format(question, options[0], options[1], options[2])
    print('Googling: {}'.format(what_to_google))
    search_results = google_search(what_to_google)

    get_answer(search_results, question, options)
    toc = time.time()
    print('Took {} seconds'.format(toc-tic))


def get_answer(google_results, question, options):
    # Build the entire description body containing all results
    result_body = ''
    for result in google_results:
        result_body += result['description']

    result_body_tokens = word_tokenize(result_body)
    result_body_tokens = [token for token in result_body_tokens if token.isalpha()]
    porter_stem = PorterStemmer()
    result_body_tokens = [porter_stem.stem(token) for token in result_body_tokens]

    # Weigh different options
    options_with_weights = []
    for option in options:
        option = option.lower()
        option_tokens = word_tokenize(option)
        option_tokens = [porter_stem.stem(token) for token in option_tokens]
        current_token_weight = 0
        for option_token in option_tokens:
            for result_body_token in result_body_tokens:
                if option_token == result_body_token:
                    current_token_weight += float(1 / len(option_tokens))

        options_with_weights.append({
            'text': option,
            'weight': current_token_weight
        })

    options_with_weights = pd.DataFrame(options_with_weights)

    print('Question: {}'.format(question))
    print('Here are the results:')
    pprint(options_with_weights)
    if question.find('NOT') == -1:
        best_index = options_with_weights['weight'].idxmax(axis=1)
        pprint('Best answer is: {}'.format(options_with_weights["text"][best_index]))
    else:
        best_index = options_with_weights['weight'].idxmin(axis=1)
        pprint('INVERSE QUESTION! Best answer is: {}'.format(options_with_weights["text"][best_index]))


def show_prompt():
    print('Enter an option (0-1)')
    print('0) Quit')
    print('1) Find the answer from the current screen on the phone')
    return int(input("> "))


def parse_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            if 'TESSERACT_PATH' in config:
                pytesseract.pytesseract.tesseract_cmd = config['TESSERACT_PATH']
            else:
                pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract'  # default value


if __name__ == "__main__":
    main()
