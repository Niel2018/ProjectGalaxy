import time
import random
import sys
from selenium import webdriver as wd
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image

# 使用Chrome登录百度指数页面
def GetBaiduIndex():
    # 打开浏览器
    bs = wd.Chrome()
    if bs is None:
        print("bs is None")
        return -1

    execute_url = bs.command_executor._url
    session_id = bs.session_id

    # 保存session_id
    #file = open(r"d:\aaa\bsinfo.txt", 'w')
    #file.write("%s %d" % execute_url, session_id)
    #file.close()

    # 等待和修改窗口大小，避免被认为是爬虫
    bs.implicitly_wait(20)
    bs.set_window_size(1000, 800)

    # 打开网址
    bs.get("http://index.baidu.com/")
    print("0")

    # 等待和修改窗口大小，避免被认为是爬虫
    time.sleep(1)
    bs.set_window_size(1200, 1000)
    time.sleep(1)
    bs.set_window_size(1000, 800)

    # 打开用户名密码框
    bs.find_element_by_class_name("username-text").click()
    time.sleep(3)
    print("0.1")

    # 输入用户名密码，登录
    username_form = bs.find_element_by_id("TANGRAM__PSP_4__userName")
    password_form = bs.find_element_by_id("TANGRAM__PSP_4__password")
    username_form.clear()
    password_form.clear()

    username = "Niel2018"
    password = "bd821230"

    # 循环输入用户名和密码
    for i in username:
        username_form.send_keys(i)
        time.sleep(0.4)
    for i in password:
        password_form.send_keys(i)
        time.sleep(0.4)

    time.sleep(1)
    action = ActionChains(bs)
    submit_button = bs.find_element_by_id("TANGRAM__PSP_4__submit")
    action.move_to_element(submit_button).click().perform()

    # 保存cookie
    # cookies = bs.get_cookies()
    # cookie = bs.get_cookie(bs, ["niel2018", "bd821230"])
    print("1")

    # 输入搜索关键字并搜索
    #search_input_form = bs.find_element_by_xpath("""//*[@id="search-input-form"]/input[3]""")
    search_input_form = bs.find_element_by_xpath("//form[@id='search-input-form']/input[3]")
    if search_input_form is None:
        print("search_input_form is None")
        return -1
    print("2")
    search_input_form.clear()
    search_input_form.send_keys("比亚迪")
    time.sleep(5)
    #home_button = bs.find_element_by_xpath("""//*[@id="home"]/div[2]/div[2]/div/div[1]/div/div[2]/div/span/span""")
    home_button = bs.find_element_by_xpath("//div[@id='home']/div[2]/div[2]/div/div/div/div[2]/div")
    if home_button is None:
        print("home_button is None")
        return -1
    print("3")
    home_button.click()
    time.sleep(5)
    bs.maximize_window()
    time.sleep(2)

    # 选择搜索时长,选为90天
    bs.find_element_by_xpath("//div[2]/button/span").click()
    bs.find_element_by_xpath("//div[3]/div/div/div[4]").click()

    # 遍历画布
    canvas = bs.find_element_by_xpath("//canvas")
    canvas_left = canvas.location['x']
    canvas_top = canvas.location['y']
    # canvas_width = s1.size['width']
    # canvas_height = s1.size['height']

    for num in range(90):
        # 显示每天的热点量
        actions = ActionChains(bs)
        left_diff = num*13
        top_diff = 200
        actions.move_to_element_with_offset(canvas, left_diff, top_diff).perform()

        # 保存为图片
        bs.save_screenshot(r'd:\aaa\screen_shoot.png')
        img = Image.open(r'd:\aaa\screen_shoot.png')
        crop_left = canvas_left + left_diff + 10
        crop_top = canvas_top + top_diff
        crop_right = crop_left + 140
        crop_bottom = crop_top + 90

        img = img.crop((crop_left, crop_top, crop_right, crop_bottom))
        target_file = "d:\\aaa\\" + str(num) + ".png"
        img.save(target_file)
        del actions

    # 找到平均日流量
    # s1 = bs.find_elements_by_css_selector("[class='veui-table-cell']")
    # s1[8].text
    return
