from playwright.sync_api import sync_playwright
import requests
from bs4 import BeautifulSoup 
import time
from twocaptcha import TwoCaptcha
import re

if '__main__' == __name__:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, timeout=60_000)
        url = "https://cotizador.mapfre.cl/CotizadorVehiculos/load.aspx?R=53616C7465645F5F53616C7465645F5F58C2C9F219409C36BEFAC6617E16F623&conv=53616C7465645F5F53616C7465645F5F7B69EF070588689C"
        page = browser.new_page()
        page.goto(url, timeout=120_000)
        with page.expect_response(lambda res: res.url.startswith("https://cotizador.mapfre.cl/CotizadorVehiculos/Default.aspx")) as res:
            with page.expect_request_finished() as _:
                page.locator("#ctl00_ContentPlaceHolder1_patente").fill("KLKP82")
                page.locator("#ctl00_ContentPlaceHolder1_patente").press("Enter")
        with page.expect_response(lambda res: res.url.startswith("https://cotizador.mapfre.cl/CotizadorVehiculos/Default.aspx")) as res:
            with page.expect_request_finished() as _:
                page.locator("#ctl00_ContentPlaceHolder1_marca").select_option("VOLKSWAGEN")
                page.locator("#ctl00_ContentPlaceHolder1_modelo").select_option("VIRTUS")
                page.locator("#ctl00_ContentPlaceHolder1_ano").select_option("2023")
                page.locator("#ctl00_ContentPlaceHolder1_txtCodDocumAseg").fill("14557325-4")
                page.locator("#ctl00_ContentPlaceHolder1_txtCodDocumAseg").press("Enter")
        with page.expect_response(lambda res: res.url.startswith("https://cotizador.mapfre.cl/CotizadorVehiculos/Default.aspx")) as res:
            with page.expect_request_finished() as _:
                html = res.value.text()
                soup = BeautifulSoup(html, 'html.parser')
                first_name_element = soup.find('input', {'id': 'ctl00_ContentPlaceHolder1_txtNomAseg'})
                middle_name_element = soup.find('input', {'id': 'ctl00_ContentPlaceHolder1_txtApePatAseg'})
                last_name_alement = soup.find('input', {'id': 'ctl00_ContentPlaceHolder1_txtApeMatAseg'})
                email_element = soup.find('input', {'id': 'ctl00_ContentPlaceHolder1_txtCorreo'})
                email_confirm_element = soup.find('input', {'id': 'ctl00_ContentPlaceHolder1_txtCorreoConf'})
                phone_element = soup.find('input', {'id': 'ctl00_ContentPlaceHolder1_txtCelular'})
                insured_first_name = first_name_element.get('value', '')
                insured_middle_name = middle_name_element.get('value', '')
                insured_last_name = last_name_alement.get('value', '')
                email = email_element.get('value', '')
                email_confirm = email_confirm_element.get('value', '')
                phone = phone_element.get('value', '')
                print(insured_first_name )
                print(insured_middle_name )
                print(insured_last_name )
                print(email)
                print(email_confirm)
                print(phone)

                

                if not insured_first_name:
                    print("first name is equal None")
                    page.locator("#ctl00_ContentPlaceHolder1_txtNomAseg").click()
                    time.sleep(0.5)
                    page.locator("#ctl00_ContentPlaceHolder1_txtNomAseg").fill("JOSE")
                    time.sleep(0.5)
                    page.locator("#ctl00_ContentPlaceHolder1_txtNomAseg").press("Enter")

                if not insured_middle_name:
                    page.locator("#ctl00_ContentPlaceHolder1_txtApePatAseg").click()
                    time.sleep(0.5)
                    page.locator("#ctl00_ContentPlaceHolder1_txtApePatAseg").fill("LOPES")
                    time.sleep(0.5)
                    #page.locator("#ctl00_ContentPlaceHolder1_txtApePatAseg").press("Enter")

                if not insured_last_name:
                   
                    page.locator("#ctl00_ContentPlaceHolder1_txtApeMatAseg").click()
                    time.sleep(0.5)
                    page.locator("#ctl00_ContentPlaceHolder1_txtApeMatAseg").fill("SILVA")
                    time.sleep(0.5)
                    page.locator("#ctl00_ContentPlaceHolder1_txtCorreo").press('Enter')
                    
                if not email:
                    page.locator("#ctl00_ContentPlaceHolder1_txtCorreo").click()
                    time.sleep(0.5)
                    page.locator("#ctl00_ContentPlaceHolder1_txtCorreo").fill("TEST@TEST.COM")
                    time.sleep(0.5)
                    #page.locator("#ctl00_ContentPlaceHolder1_txtCorreo").press("Enter")
                    
                if not email_confirm:
                    page.locator("#ctl00_ContentPlaceHolder1_txtCorreoConf").click()
                    time.sleep(0.5)
                    page.locator("#ctl00_ContentPlaceHolder1_txtCorreoConf").fill("TEST@TEST.COM")
                    time.sleep(0.5)
                    #page.locator("#ctl00_ContentPlaceHolder1_txtCorreoConf").press("Enter")

                if not phone:
                   page.get_by_placeholder("Ej. 984765422").click()
                   time.sleep(0.5)
                   page.get_by_placeholder("Ej. 984765422").fill("958644223")
                   time.sleep(0.5)
                   page.get_by_placeholder("Ej. 984765422").press("Enter")

                   page.locator("#ctl00_ContentPlaceHolder1_rdbFranquiciaNo").check()
                   time.sleep(0.5)
                   page.locator("#ctl00_ContentPlaceHolder1_hijosNo").check()
                   time.sleep(0.5)
                   page.locator("#ctl00_ContentPlaceHolder1_usoSi").check()
                   time.sleep(0.5)
        with page.expect_response(        lambda res: res.url.startswith(            "https://www.google.com/recaptcha/api2"        )    ):
            iframe = page.frame_locator('iframe[title="reCAPTCHA"]')
            iframe.locator("div.recaptcha-checkbox-border").click()
            page.wait_for_load_state('load') # da muito timeout aqui
            # iframe_captcha = page.locator("rc-imageselect-response-field")
            #title = 'recaptcha challenge expires in two minutes'
            title = 'reCAPTCHA'
            selector = f'iframe[title^="{title}"]'
            recaptcha_challenges = page.query_selector_all(selector)
            q_challenges = len(recaptcha_challenges)
            print(q_challenges)
            #recaptcha_challenges = bool(recaptcha_challenges)
            print(recaptcha_challenges)
            print(recaptcha_challenges[q_challenges - 1].is_visible())
            if recaptcha_challenges[q_challenges - 1].is_visible():
                print('🤖 RECAPTCHA visible ...')

                with open('data/grecaptchacallback.js', 'r') as jsfile:
                    grecaptcha_callback = jsfile.read()
                    g_recaptcha_info = page.evaluate(grecaptcha_callback)
                    print(grecaptcha_callback)
                    callback = g_recaptcha_info[q_challenges + 3]['callback']
                    sitekey = g_recaptcha_info[q_challenges + 3]['sitekey']

                    # Regex que retorna 0, B y B para siguiente caso "___grecaptcha_cfg.clients['0']['B']['B']['callback']"
                    re_callback = re.findall("\['([^']+)'\]", callback) 

                    first_letter_callback = re_callback[1]
                    second_letter_callback = re_callback[2]

                    print(first_letter_callback)
                    print(second_letter_callback)


                    solver = TwoCaptcha("ffa52f3278dcca0d7505d0de8f1028cd")
                    print('🕒 Resolviendo recaptcha ...')
                    sitekey = "6Le1Ir4ZAAAAAG4brISHwJ9AIH9uJQQ6UYPLle5i"
                    result = solver.recaptcha(
                        sitekey=sitekey,
                        url='https://cotizador.mapfre.cl/CotizadorVehiculos/Default.aspx'
                    )
                    print(result["code"])
                    captcha = result["code"]
                    teste =  f"___grecaptcha_cfg.clients[3].{first_letter_callback}.{second_letter_callback}.callback('{captcha}')"
                    print(teste)
                    page.evaluate(teste)
                    page.pause()
                    page.get_by_role("button", name="Simular").click()
                    page.pause()

                    # except Exception as e:
                    #     raise e
                    # else:
                    #     print(f'\n👌 RESUELTO:', result["code"], '\n')
                    # return result['code']

                    # # captcha = get_captcha(sitekey, api_key)

                    # print(retornar)
                            
            else:
                print("else")


            page.pause()

    page.close()

    browser.close()
