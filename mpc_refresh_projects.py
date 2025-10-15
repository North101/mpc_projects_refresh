import asyncio
import os
from typing import NamedTuple

from pydoll.browser import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.browser.tab import Tab
from pydoll.constants import Key

def to_bool(value: str | None, default: bool):
  if value is None:
    return default
  return value.lower().strip() == str(True).lower()


class Config(NamedTuple):
  headless: bool
  sandbox: bool
  webgl: bool
  user_agent: str
  chrome_path: str

  username: str
  password: str


def read_config():
  return Config(
    headless=to_bool(os.getenv('PYDOLL_HEADLESS'), False),
    sandbox=to_bool(os.getenv('PYDOLL_SANDBOX'), False),
    webgl=to_bool(os.getenv('PYDOLL_WEBGL'), False),
    user_agent=os.getenv('PYDOLL_USERAGENT', ''),
    chrome_path=os.getenv('PYDOLL_CHROME_PATH', ''),

    username=os.environ['MPC_USERNAME'],
    password=os.environ['MPC_PASSWORD'],
  )


async def main(refresh_project_id: str | None = None):
  config = read_config()

  options = ChromiumOptions()
  options.headless = config.headless
  options.password_manager_enabled = False

  if config.webgl:
    options.add_argument("--enable-webgl")
  if config.sandbox:
    options.add_argument("--no-sandbox")
  if config.user_agent:
    options.add_argument(f'--user-agent="{config.user_agent}"')
  if config.chrome_path:
    options.binary_location = config.chrome_path

  async with Chrome(options) as browser:
    try:
      tab = await browser.start()
      print('login')
      await login(tab, config)
      if refresh_project_id:
        await refresh_project(tab, refresh_project_id)
      else:
        print('finding projects')
        project_ids = await find_projects(tab)
        for i, project_id in enumerate(project_ids):
          print(f'Refreshing {i + 1}/{len(project_ids)}')
          await refresh_project(tab, project_id)
    finally:
      await browser.stop()
      await asyncio.sleep(10000)


async def login(tab: Tab, config: Config):
  await tab.go_to('https://www.makeplayingcards.com/login.aspx')

  txt_email = await tab.find(id='txt_email')
  await txt_email.insert_text(config.username)
  await txt_email.press_keyboard_key(Key.ENTER)
  await asyncio.sleep(1)

  txt_password = await tab.find(id='txt_password')
  await txt_password.insert_text(config.password)
  await txt_password.press_keyboard_key(Key.ENTER)
  await asyncio.sleep(1)

  await tab.go_to('https://www.makeplayingcards.com/design/dn_temporary_designes.aspx')


async def find_projects(tab: Tab):
  project_ids = []

  await tab.go_to('https://www.makeplayingcards.com/design/dn_temporary_designes.aspx')
  while True:
    projects = await tab.query(
        "//div[@class='bmcheckbox']/input",
        find_all=True,
    )
    project_ids += [
        project_id[4:]
        for project_id in (
            project.get_attribute('id')
            for project in projects
        )
        if project_id is not None
    ]
    next_page = await tab.query(
        "//div[@id='div_navPage']//a[text()='Next']",
    )
    if not next_page.get_attribute('href'):
      break

    await next_page.click()
    await asyncio.sleep(0.5)
    await tab._wait_page_load()

  return project_ids


async def refresh_project(tab: Tab, project_id: str):
  while True:
    try:
      await tab.go_to(f'https://www.makeplayingcards.com/design/dn_temporary_parse.aspx?id={project_id}&edit=Y')
      await asyncio.sleep(1)
      break
    except:
      print(f'Retrying {project_id}')
      await asyncio.sleep(1)


asyncio.run(main())
