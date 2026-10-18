// Test-only browser dependency. Production Python requirements remain unchanged.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const [url, fixtures, output] = process.argv.slice(2);
  const options = {headless: true};
  if (process.env.VELA_QA_BROWSER) options.executablePath = process.env.VELA_QA_BROWSER;
  const browser = await chromium.launch(options);
  async function openMix(width) {
    const context = await browser.newContext({viewport: {width, height: 900}, acceptDownloads: true});
    const page = await context.newPage();
    page.setDefaultTimeout(60000);
    await page.goto(url);
    await page.locator('.st-key-home_action_Cut_Audio button').click();
    await page.getByRole('radio', {name: 'Mix stems', exact: true}).locator('..').click();
    await page.getByRole('button', {name: 'Create WAV mix', exact: true}).waitFor();
    return {context, page};
  }
  async function upload(page, vocal, music) {
    await page.locator('input[type=file]').nth(0).setInputFiles(path.join(fixtures, vocal));
    await page.locator('input[type=file]').nth(1).setInputFiles(path.join(fixtures, music));
    await page.getByRole('button', {name: 'Create WAV mix', exact: true}).click();
  }
  async function download(page, filename) {
    const ready = page.getByText('WAV mix ready', {exact: false});
    await ready.waitFor();
    const pending = page.waitForEvent('download');
    await page.getByRole('button', {name: 'Download WAV mix', exact: true}).click();
    const result = await pending;
    assert.equal(await result.failure(), null);
    await result.saveAs(path.join(output, filename));
  }
  try {
    const a = await openMix(1440);
    const b = await openMix(390);
    await Promise.all([
      upload(a.page, 'vocal.wav', 'instrumental.wav'),
      upload(b.page, 'silence.wav', 'silence.wav')
    ]);
    await download(a.page, 'mix.wav');
    await download(a.page, 'mix-repeat.wav');
    await download(b.page, 'silent.wav');
    assert.deepEqual(fs.readFileSync(path.join(output, 'mix.wav')), fs.readFileSync(path.join(output, 'mix-repeat.wav')));
    assert.notDeepEqual(fs.readFileSync(path.join(output, 'mix.wav')), fs.readFileSync(path.join(output, 'silent.wav')));
    await a.page.getByRole('button', {name: 'Clear temporary mix', exact: true}).click();
    await a.page.getByRole('button', {name: 'Download WAV mix', exact: true}).waitFor({state: 'detached'});
    // Session A clearing its download cannot clear Session B's download.
    await download(b.page, 'silent-after-other-session-clear.wav');
    await upload(a.page, 'vocal.wav', 'instrumental.wav');
    await download(a.page, 'mix-regenerated.wav');
    assert.deepEqual(fs.readFileSync(path.join(output, 'mix.wav')), fs.readFileSync(path.join(output, 'mix-regenerated.wav')));
    await a.page.locator('input[type=file]').nth(0).setInputFiles(path.join(fixtures, 'corrupt.wav'));
    await a.page.getByRole('button', {name: 'Create WAV mix', exact: true}).click();
    await a.page.getByText('Mix could not be rendered or measured', {exact: false}).waitFor();
    assert.equal(await a.page.getByRole('button', {name: 'Download WAV mix', exact: true}).count(), 0);
    await a.page.locator('input[type=file]').nth(0).setInputFiles(path.join(fixtures, 'oversized.wav'));
    await a.page.getByText('Each stem must be nonempty and at most 64 MB.', {exact: true}).waitFor();
    assert.equal(await a.page.getByRole('button', {name: 'Create WAV mix', exact: true}).isDisabled(), true);
    // Rerender after invalid input must not expose stale output.
    await b.page.screenshot({path: path.join(output, 'mix-mobile.png'), fullPage: true});
    await a.page.screenshot({path: path.join(output, 'corrupt-desktop.png'), fullPage: true});
    const overflow = await b.page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    assert.equal(overflow, false, 'mobile horizontal overflow');
    console.log(JSON.stringify({passed: true, scenarios: [
      'full-app upload to WAV download', 'mismatched durations', 'silent audio',
      'repeat download', 'clear and regenerate', 'corrupt input/stale result invalidation',
      'two browser sessions with distinct results', 'mobile no horizontal overflow',
      'real oversized browser upload rejected before processing'
    ]}));
    await a.context.close();
    await b.context.close();
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
