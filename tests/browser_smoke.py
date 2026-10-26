"""Real browser -> API -> backend -> WebSocket -> second browser page.
Run only against a dedicated test instance; game settings are reset to defaults.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8000')
parser.add_argument('--output', default='runtime/browser-tests')
args = parser.parse_args()
output = Path(args.output)
output.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    options = {'headless': True}
    if Path('/usr/bin/chromium').exists():
        options.update(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    browser = p.chromium.launch(**options)
    context = browser.new_context(viewport={'width':1440,'height':1000})
    errors = []
    external_requests = []
    def api(action,value=None):
        response = context.request.post(args.url+'/api/command',data={'action':action,'value':value})
        assert response.ok, response.text()
        return response.json()
    def reset_defaults():
        api('reset'); api('mode','manual'); api('code','4279'); api('duration',3600); api('require_human_approval',False)
        api('presentation', {})
    reset_defaults()
    dashboard = context.new_page()
    dashboard.on('pageerror', lambda error: errors.append(str(error)))
    dashboard.on('request',lambda r: external_requests.append(r.url) if not r.url.startswith((args.url, 'data:', 'blob:')) else None)
    dashboard.goto(args.url)
    expect(dashboard.get_by_role('heading',name='Huoneen ohjaus.')).to_be_visible()
    player = context.new_page()
    player.on('pageerror',lambda error:errors.append(str(error)))
    player_payloads=[]
    def record_socket(socket):
        socket.on('framereceived',lambda frame:player_payloads.append(json.loads(frame)) if isinstance(frame,str) else None)
    player.on('websocket',record_socket)
    player.goto(args.url+'/player')
    expect(player.get_by_text('odotetaan seuraavan pelin käynnistystä...', exact=True)).to_be_visible()
    assert player.locator('button').count() == 0
    assert player.locator('input,select').count() == 0
    dashboard.screenshot(path=str(output/'dashboard.png'),full_page=True)
    player.screenshot(path=str(output/'player.png'))

    dashboard.get_by_role('button',name='Aloita pre-game näkymä',exact=True).click()
    expect(player.get_by_role('heading',name='Tervetuloa pakohuoneeseen!',exact=True)).to_be_visible()
    dashboard.get_by_role('button',name='Seuraava dia',exact=True).click()
    expect(player.locator('.intro-sequence')).to_be_visible()
    assert context.request.get(args.url+'/api/state').json()['running'] is False
    dashboard.get_by_role('button',name='Seuraava dia',exact=True).click()
    expect(player.locator('.intro-movement')).to_be_visible()
    dashboard.get_by_role('button',name='Käynnistä peli',exact=True).click()
    expect(dashboard.get_by_role('button',name='Pysäytä ajastin')).to_be_enabled()
    dashboard.wait_for_timeout(1100)
    dashboard.get_by_role('button',name='Pysäytä ajastin').click()
    expect(dashboard.get_by_role('button',name='Jatka peliä')).to_be_enabled()
    expect(player.locator('.player-countdown')).to_have_text(dashboard.locator('.timer-value').inner_text())
    frozen=player.locator('.player-countdown').inner_text()
    player.wait_for_timeout(500)
    assert player.locator('.player-countdown').inner_text() == frozen
    print('PASS: timer start, pause and two-page synchronization')

    for i,digit in enumerate('4278',1):
        dashboard.get_by_role('textbox',name=f'Testinumero {i}',exact=True).fill(digit)
        expect(dashboard.get_by_role('textbox',name=f'Testinumero {i}',exact=True)).to_have_value(digit)
    expect(player.locator('.player-indicator.correct')).to_have_count(0)
    small_width=player.locator('.player-lamp').first.bounding_box()['width']
    dashboard.get_by_role('button',name='Seuraava näkymä',exact=True).click()
    expect(player.locator('.view-lights-off')).to_be_visible()
    dashboard.get_by_role('button',name='Seuraava näkymä',exact=True).click()
    expect(player.locator('.view-digits')).to_be_visible()
    expect(player.locator('.player-indicator.correct')).to_have_count(0)
    player.wait_for_timeout(700)
    assert player.locator('.player-lamp').first.bounding_box()['width'] > small_width
    dashboard.get_by_role('textbox',name='Testinumero 4',exact=True).fill('9')
    expect(player.get_by_role('heading',name='Huone ratkaistu')).to_be_visible()
    expect(player.locator('.result-victory')).to_be_visible()
    expect(player.locator('.solution-summary.is-visible')).to_be_visible()
    expect(player.locator('.solution-slot')).to_have_count(4)
    player.wait_for_timeout(1200)  # Let the success reveal reach full opacity.
    player.screenshot(path=str(output/'player-success.png'))
    dashboard.get_by_role('button',name='Nollaa huone',exact=True).click()
    dashboard.locator('dialog').get_by_role('button',name='Nollaa huone',exact=True).click()
    expect(player.get_by_text('odotetaan seuraavan pelin käynnistystä...', exact=True)).to_be_visible()
    expect(player.locator('.player-indicator.correct')).to_have_count(0)
    print('PASS: neutral player digits, full-code success animation and reset')

    dashboard.get_by_role('button',name='Peliasetukset',exact=True).click()
    dashboard.get_by_role('textbox',name='Oikea koodi',exact=True).fill('0138')
    dashboard.get_by_role('button',name='Tallenna peliasetukset',exact=True).click()
    expect(dashboard.get_by_role('button',name='Tallenna peliasetukset',exact=True)).to_be_disabled()
    dashboard.reload()
    expect(dashboard.get_by_role('textbox',name='Oikea koodi',exact=True)).to_have_value('0138')
    assert context.request.get(args.url+'/api/state').json()['code']=='0138'
    dashboard.get_by_role('button',name='Takaisin peliin',exact=True).click()
    print('PASS: code editing, leading zero and persisted settings')

    dashboard.locator('.camera-disclosure > summary').click()
    dashboard.get_by_role('button',name='Säädä alueita').click()
    x_field=dashboard.get_by_role('spinbutton',name='X %',exact=True)
    x_field.fill('9.5')
    x_field.press('Tab')
    expect(dashboard.get_by_role('button',name='Alueet tallennettu',exact=True)).to_be_visible()
    assert abs(context.request.get(args.url+'/api/state').json()['regions'][0]['x']-.095)<.001
    first=dashboard.locator('.roi').first.bounding_box()
    dashboard.mouse.move(first['x']+20,first['y']+20)
    dashboard.mouse.down(); dashboard.mouse.move(first['x']+36,first['y']+24,steps=5); dashboard.mouse.up()
    expect(dashboard.get_by_role('button',name='Alueet tallennettu',exact=True)).to_be_visible()
    assert context.request.get(args.url+'/api/state').json()['regions'][0]['x']>.095
    print('PASS: numeric and pointer-based region calibration')

    expect(dashboard.get_by_role('button',name='Simuloi ratkaisu')).to_have_count(0)
    expect(player.locator('audio')).to_have_count(0)
    api('reset'); api('duration',2)
    expect(dashboard.locator('.timer-value')).to_have_text('00:02.000')
    dashboard.get_by_role('button',name='Aloita pre-game näkymä',exact=True).click()
    expect(player.get_by_role('heading',name='Tervetuloa pakohuoneeseen!',exact=True)).to_be_visible()
    dashboard.get_by_role('button',name='Seuraava dia',exact=True).click()
    expect(player.locator('.intro-sequence')).to_be_visible()
    assert context.request.get(args.url+'/api/state').json()['running'] is False
    dashboard.get_by_role('button',name='Seuraava dia',exact=True).click()
    expect(player.locator('.intro-movement')).to_be_visible()
    dashboard.get_by_role('button',name='Käynnistä peli',exact=True).click()
    expect(player.get_by_role('heading', name='AIKA LOPPUI', exact=True)).to_be_visible(timeout=5000)
    print('PASS: no simulation option, silent player display and timeout')

    # Reopening a page receives the current authoritative terminal state.
    player.reload()
    expect(player.get_by_role('heading', name='AIKA LOPPUI', exact=True)).to_be_visible()
    assert all('code' not in item['state'] and 'events' not in item['state'] for item in player_payloads)
    print('PASS: player reconnect and no target code in player WebSocket payloads')

    reset_defaults()
    default_regions=[{'x':.085+i*.225,'y':.25,'width':.155,'height':.5} for i in range(4)]
    api('regions',default_regions)
    dashboard.get_by_role('button',name='Kamera',exact=True).click()
    expect(dashboard.locator('.camera-empty')).to_be_visible()
    dashboard.get_by_role('button',name='Manuaalinen',exact=True).click()
    expect(dashboard.locator('.demo-scene')).to_be_visible()

    for width in [390,768,1024]:
        dashboard.set_viewport_size({'width':width,'height':844})
        assert dashboard.locator('body').evaluate('(el)=>el.scrollWidth') == width
    dashboard.set_viewport_size({'width':390,'height':844})
    dashboard.screenshot(path=str(output/'dashboard-mobile.png'),full_page=True)
    player.set_viewport_size({'width':390,'height':844})
    assert player.locator('body').evaluate('(el)=>el.scrollWidth') == 390
    assert player.locator('.player-waiting').bounding_box()['width'] <= 390
    player.screenshot(path=str(output/'player-mobile.png'))
    assert not errors, errors
    assert not external_requests, external_requests
    print('PASS: responsive layouts, zero browser errors, no external network dependencies')
    context.close(); browser.close()
print('All browser smoke checks passed.')
