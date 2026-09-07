// Run in a dedicated helper session with a waiting test agent. All drawings are fixtures.
async (page) => {
  const checks = [];
  const assert = (value, label) => { if (!value) throw new Error(label); checks.push(label); };
  const canvas = page.getByLabel('Drawing canvas. Draw with a mouse, finger, or stylus.', {exact: true});
  const use = page.locator('#use-sketch');
  await page.setViewportSize({width:1280, height:720});
  await Promise.all([
    page.waitForResponse(response => response.url().endsWith('/api/session')),
    page.reload(),
  ]);
  assert(await use.isDisabled(), 'Blank sketch cannot be sent');
  const draw = async y => {
    const rect = await canvas.boundingBox();
    await page.mouse.move(rect.x + 30, rect.y + y);
    await page.mouse.down();
    await page.mouse.move(rect.x + 160, rect.y + y, {steps:20});
    await page.mouse.up();
  };
  await draw(50);
  const expected = await canvas.evaluate(el => el.toDataURL().split(',')[1]);
  const requests = [];
  await page.route('**/api/sketch', async route => {
    requests.push({id:route.request().headers()['x-submission-id'], body:route.request().postDataBuffer().toString('base64')});
    await route.continue();
  });
  const firstResponse = page.waitForResponse(response => response.url().endsWith('/api/sketch'));
  await use.click();
  const first = await (await firstResponse).json();
  await page.waitForFunction(() => document.querySelector('#use-sketch').textContent.includes('Sketch sent'));
  assert(first.status === 'submitted', 'Use sketch submits successfully to the real helper');
  assert(first.agent_waiting, 'The helper sees the test agent waiting');
  assert(requests[0].body === expected, 'Submitted PNG is exactly the visible canvas');
  assert(await use.isDisabled(), 'Same drawing cannot be accidentally sent twice');
  assert(await page.getByRole('button', {name:'Copy image', exact:true}).isEnabled(), 'Copy remains available after handoff');

  await draw(110);
  assert(await use.isEnabled(), 'A changed drawing can be submitted again');
  const changed = await canvas.evaluate(el => el.toDataURL());
  await page.unroute('**/api/sketch');
  let lostId;
  let savedSeq;
  await page.route('**/api/sketch', async route => {
    lostId = route.request().headers()['x-submission-id'];
    const response = await route.fetch();
    savedSeq = (await response.json()).seq;
    await route.abort('failed'); // Server accepted the PNG, but the response was lost.
  });
  await use.click();
  await page.waitForFunction(() => document.querySelector('#status').textContent.includes('not confirmed'));
  assert(await canvas.evaluate(el => el.toDataURL()) === changed, 'Network failure preserves the drawing');
  await page.unroute('**/api/sketch');
  let retryId;
  await page.route('**/api/sketch', async route => {
    retryId = route.request().headers()['x-submission-id'];
    await route.continue();
  });
  const retryResponse = page.waitForResponse(response => response.url().endsWith('/api/sketch'));
  await use.click();
  const retry = await (await retryResponse).json();
  await page.waitForFunction(() => document.querySelector('#use-sketch').textContent.includes('Sketch sent'));
  assert(lostId === retryId && retry.seq === savedSeq, 'Retry after a lost response reuses the same saved reference');
  assert(retry.seq === first.seq + 1, 'Only distinct drawings create new submission events');
  await page.setViewportSize({width:390, height:844});
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Three export buttons fit on mobile');
  await page.screenshot({path:'output/playwright/canvas2imagegen-use-button.png', fullPage:true});
  return {passed:checks.length, checks, firstSeq:first.seq, lastSeq:retry.seq};
}
