import re
from datetime import datetime
import json

import gspread
import pandas as pd
from playwright.sync_api import Page
from twocaptcha import TwoCaptcha
import time
#import cloudscraper as scraper


def get_captcha(sitekey: str, api_key: str):
    solver = TwoCaptcha(api_key)
    try:
        print('🕒 Resolviendo recaptcha ...')
        result = solver.recaptcha(
            sitekey=sitekey,
            url='https://auto.segurosfalabella.com/'
        )
    except Exception as e:
        raise e
    else:
        print(f'\n👌 RESUELTO:', result["code"], '\n')
    return result['code']


def solve_recaptcha(page: Page, api_key: str):

    page.wait_for_load_state('networkidle')
    title = 'recaptcha challenge expires in two minutes'
    selector = f'iframe[title^="{title}"]'
    recaptcha_challenges = page.query_selector_all(selector)
    q_challenges = len(recaptcha_challenges)

    if q_challenges == 0:
        return None

    if recaptcha_challenges[q_challenges - 1].is_visible():
        print('🤖 RECAPTCHA visible ...')

        with open('data/grecaptchacallback.js', 'r') as jsfile:
            grecaptcha_callback = jsfile.read()

        g_recaptcha_info = page.evaluate(grecaptcha_callback)
        callback = g_recaptcha_info[q_challenges - 1]['callback']
        sitekey = g_recaptcha_info[q_challenges - 1]['sitekey']

        # Regex que retorna 0, B y B para siguiente caso "___grecaptcha_cfg.clients['0']['B']['B']['callback']"
        re_callback = re.findall("(?<=\[\').*?(?=\'\])", callback)
        first_letter_callback = re_callback[1]
        second_letter_callback = re_callback[2]

        captcha = get_captcha(sitekey, api_key)
        return f"___grecaptcha_cfg.clients[{q_challenges - 1}].{first_letter_callback}.{second_letter_callback}.callback('{captcha}')"
    
    else:
        return None
    

def parse_data(request: dict, response: dict, transaction_item: dict[str, str]) -> pd.DataFrame:
        
    df_response = pd.DataFrame(response['response']['plans'])
    
    columns = [
        'car',
        'brand',
        'model',
        'year',
        'plate',
        'rut',
        'birthdate',
        'comune',
        'email',
        'celular',
        'company',
        'product company',
        'compara product name',
        'company product name',
        'deductible',
        'price',
        'execute date',
        'quote ID',
        'obs',
        'execution time'
    ]

    df_final = pd.DataFrame(columns=columns)

    df_final['deductible'] = df_response['deductible'].astype(float).astype(int)
    df_final['company'] = 'Falabella'
    df_final['product company'] = df_response['company'].str['name']

    product_companies = {
        'BCI SEGUROS GENERALES S.A.': 'BCI Seguros',
        'COMPAÑIA DE SEGUROS GENERALES CONSORCIO': 'Consorcio',
        'HDI SEGUROS S.A.': 'HDI',
        'ZENIT SEGUROS GENERALES S.A.': 'Zenit Seguros',
        'ZURICH CHILE SEGUROS GENERALES S.A.': 'Zurich',
        'FID CHILE SEGUROS GENERALES S.A.': 'FID',
        'LIBERTY CIA DE SEGUROS GENERALES S.A': 'Liberty'
    }

    df_final = df_final.replace({'product company': product_companies})
    df_final['company product name'] = df_response['description']

    plate = transaction_item['plate'].strip()
    comune = transaction_item['comune'].strip()
    email = transaction_item['email'].strip()
    phone = transaction_item['celular'].strip()

    df_final['plate'] = plate
    df_final['comune'] = comune
    df_final['email'] = email
    df_final['celular'] = phone

    df_final['car'] = f"{request['brand']} {request['model']}"
    df_final['brand'] = request['brand']
    df_final['model'] = request['model']
    df_final['year'] = request['year']
    df_final['rut'] = f"{request['documentNumber']}-{request['verificationDigit']}"
    df_final['birthdate'] = datetime.strptime(request['birthdate'], '%Y-%m-%d').strftime('%d-%m-%Y')
    df_final['price'] = df_response['moneyCLP'].apply(lambda x: str(x).replace('.', '')).astype('int')
    df_final['execute date'] = datetime.today().strftime('%d/%m/%Y')
    df_final['execution time'] = datetime.now().strftime('%H:%M:%S')
    
    # TODO
    df_final['compara product name'] = ''
    df_final['quote ID'] = ''
    df_final['obs'] = ''

    df_final = df_final.fillna('')
    return df_final


def homologation(df: pd.DataFrame, config: dict):
    print('Homologando Productos a Compara.')
    gc = gspread.service_account(filename='data/gspread_credentials.json')
    ws = gc.open(config['google_sheet']).worksheet(config['broker_homologation'])
    df_homologation = pd.DataFrame(ws.get_all_records())
    df_homologation = df_homologation.loc[df_homologation['company'] == 'Falabella']
    homologation_dict = df_homologation.to_dict('records')
    for homologation in homologation_dict:
        df.loc[
            (df['product company'] == homologation['product company']) & 
            (df['company product name'] == homologation['company product name']), 
            'compara product name'] = homologation['compara product name']
    df.loc[df['compara product name'] == '', 'obs'] = 'No se pudo homologar producto' 
    return df


def write_to_google_sheets(df: pd.DataFrame, config: dict):
    gc = gspread.service_account(filename='data/gspread_credentials.json')
    ws = gc.open(config['google_sheet']).worksheet(config['sheet_write'])
    ws.append_rows(df.values.tolist())

    
def run(page: Page, transaction_item: dict[str, str], config: dict) -> None:
    
    rut = transaction_item['rut'].strip()
    brand = transaction_item['brand'].strip()
    model = transaction_item['model'].strip()
    year = transaction_item['year'].strip()
    email = transaction_item['email'].strip()
    phone = transaction_item['celular'].strip()
    birthdate = transaction_item['birthdate'].strip()
    two_captcha_key = config['twocaptcha_key']
    
    # response = scraper.get('https://auto.segurosfalabella.com/') #test
    # page.content = response.text #test
    # print(response)

    page.goto('https://auto.segurosfalabella.com/')
    print('\n😄 RUT:', rut)
    page.get_by_placeholder("¿Me indicas tu RUT?").type(rut)
    

    # Chequear si se solicita fecha de nacimiento
    birthdate_requested = False

    # with scraper.get('https://auto.segurosfalabella.com/api/people', stream=True) as res: #test

    with page.expect_response(lambda res: res.url.startswith('https://auto.segurosfalabella.com/api/people')) as res: #test voltar uma identacao
        with page.expect_request_finished() as _:
            page.get_by_role("button", name="Continuar").click()
        js_submit = solve_recaptcha(page, two_captcha_key)
        if js_submit:
            page.evaluate(js_submit)

    people_response = res.value.text()
    if "auto.segurosfalabella.com used Cloudflare to restrict access" in people_response:
        now = datetime.now()
        print(f"Sleeping  process because block page - {now}")
        time.sleep(350)
        raise Exception("Cloudflare block detected")
        
    print(people_response)
    json_response = json.loads(people_response)

    
    mail_in_response = False
    if json_response['statusCode'] == 200:
        # Checkear si correo está en registros de falabella (selector de correo varía dependiendo de esto)
        if '@' in json_response['response']['email']:
            mail_in_response = True

    elif json_response['statusCode'] == 404:
        birthdate_requested = True
        # Chequear formato de fecha
        pattern = r'\b\d{2}-\d{2}-\d{4}\b' # Regex para dd-mm-yyyy
        bd_matches = re.search(pattern, birthdate)
        if not bd_matches:
            print('😔 Fecha de nacimiento no tiene formato correcto')
            return
        birthdate_selector = 'input[placeholder="dd-mm-aaaa"]'
        page.locator(birthdate_selector).fill(birthdate)
        page.get_by_role("button", name="Continuar").click()
    

    print('🚗 MARCA:', brand)
    page.get_by_text('¿Cuál es la marca?').click()

    page.locator("#react-select-2--value").get_by_role("combobox").fill(brand)
    page.wait_for_selector(f'div[role="option"][aria-label="{brand}"]')
    select_brand = page.query_selector(f'div[role="option"][aria-label="{brand}"]')
    select_brand.focus()
    brands_endpoint = 'https://auto.segurosfalabella.com/api/vehicle-brands'
    with page.expect_response(lambda res: res.url.startswith(brands_endpoint)) as res:
        select_brand.press("Enter")
    models_response = res.value.json()
    model_found = any(True for m in models_response['response'] if model == m['label'])
    if not model_found:
        print(f'😔 Modelo {model} no existe literalmente en Falabella')
        return

    print('🚕 MODELO:', model)
    page.locator("#react-select-3--value").get_by_role("combobox").fill(model)
    page.wait_for_selector(f'div[role="option"][aria-label="{model}"]')
    select_model = page.query_selector(f'div[role="option"][aria-label="{model}"]')
    select_model.focus()
    select_model.press("Enter")

    print('⌛ AÑO:', year)
    page.get_by_text("¿De qué año?").click()
    page.locator("#react-select-4--value").get_by_role("combobox").type(str(year))
    page.keyboard.press('Enter')
    page.get_by_role("button", name="Continuar").click()

    print('📭 EMAIL:', email)
    if birthdate_requested or not mail_in_response:
        page.locator('input.input-control[placeholder="¿Cuál es tu correo?"]').fill(email)
    else:
        page.locator('input.input-control[placeholder*="@"]').fill(email)
    print('☎️ TELEFONO:', phone)
    page.get_by_placeholder("¿Cuál es tu teléfono?").fill(phone)
    page.get_by_role("button", name="Cotizar el mejor seguro").click(trial=True)


    url_start = 'https://auto.segurosfalabella.com/api/quotes'
    with page.expect_response(lambda res: res.url.startswith(url_start)) as res, \
        page.expect_request(lambda req: req.url.startswith(url_start)) as req:
        page.get_by_role("button", name="Cotizar el mejor seguro").click()
        print('🕒 Esperando respuesta endpoint:', url_start)
        js_submit = solve_recaptcha(page, two_captcha_key)
        if js_submit:
            page.evaluate(js_submit)
        else:
            pass
        json_request = req.value.post_data_json
        json_response = res.value.json()
    df = parse_data(json_request, json_response, transaction_item)
    df = homologation(df, config)
    write_to_google_sheets(df, config)