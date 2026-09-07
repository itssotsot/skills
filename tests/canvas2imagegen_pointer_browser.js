// Playwright CLI run-code regression; use a dedicated test page, never a user's draft.
async (page) => {
  const checks = [];
  const assert = (condition, label) => {
    if (!condition) throw new Error(label);
    checks.push(label);
  };
  const canvas = page.getByLabel('Drawing canvas. Draw with a mouse, finger, or stylus.', { exact: true });
  const button = name => page.getByRole('button', { name, exact: true });
  const snapshot = () => canvas.evaluate(el => el.toDataURL());
  const flush = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const prepare = async () => {
    await page.reload();
    await canvas.evaluate(el => el.addEventListener('pointerdown', event => { el.dataset.testPointer = event.pointerId; }));
    return canvas.boundingBox();
  };
  const start = async rect => {
    await page.mouse.move(rect.x + 25, rect.y + 40);
    await page.mouse.down();
    await page.mouse.move(rect.x + 150, rect.y + 40, { steps: 25 });
    await flush();
  };
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.mouse.up();
  let rect = await prepare();
  await start(rect);
  const captureStroke = await snapshot();
  await canvas.evaluate(el => el.releasePointerCapture(Number(el.dataset.testPointer)));
  await page.mouse.move(rect.x + 155, rect.y + 40);
  await flush();
  assert(await snapshot() === captureStroke, 'Losing pointer capture preserves the stroke already drawn');
  await page.mouse.up();
  assert(await button('Copy image').isEnabled(), 'Interrupted stroke can be exported');
  await button('Undo').click();
  assert(await button('Copy image').isDisabled(), 'Interrupted stroke is one undo step');
  await button('Redo').click();
  assert(await snapshot() === captureStroke, 'Redo restores the interrupted stroke exactly');

  // Emulate browser cancellation after a real pointerdown/move sequence.
  rect = await prepare();
  await start(rect);
  const cancelledStroke = await snapshot();
  await canvas.evaluate(el => el.dispatchEvent(new PointerEvent('pointercancel', { pointerId: Number(el.dataset.testPointer), bubbles: true })));
  await page.mouse.up();
  await flush();
  assert(await snapshot() === cancelledStroke, 'Pointer cancellation keeps ink and adds no line to the origin');
  await button('Undo').click();
  assert(await button('Copy image').isDisabled(), 'Cancel followed by lost capture does not duplicate history');
  await button('Redo').click();
  assert(await snapshot() === cancelledStroke, 'Cancelled stroke is recoverable with redo');

  rect = await prepare();
  await start(rect);
  const blurredStroke = await snapshot();
  await page.evaluate(() => window.dispatchEvent(new Event('blur')));
  await page.mouse.up();
  assert(await button('Copy image').isEnabled() && await snapshot() === blurredStroke, 'Window focus loss commits the stroke without losing ink');

  // Hundreds of moves in a single uninterrupted drag, with a pause before release.
  rect = await prepare();
  await page.mouse.move(rect.x + 25, rect.y + 40);
  await page.mouse.down();
  for (let i = 1; i <= 240; i += 1) {
    await page.mouse.move(rect.x + 25 + i, rect.y + 100 + Math.sin(i / 8) * 50);
  }
  await flush();
  const longStroke = await snapshot();
  await page.mouse.up();
  await flush();
  assert(await snapshot() === longStroke, 'Long continuous stroke survives mouse release');
  await button('Undo').click();
  assert(await button('Copy image').isDisabled(), 'Long continuous stroke is one undo step');
  await button('Redo').click();
  assert(await snapshot() === longStroke, 'Redo restores the complete long stroke');

  // Pointer capture must also preserve a stroke released outside the paper.
  rect = await prepare();
  await start(rect);
  await page.mouse.move(rect.x + rect.width + 20, rect.y + 40, { steps: 12 });
  await page.mouse.up();
  assert(await button('Copy image').isEnabled(), 'Releasing outside the canvas preserves the stroke');
  await button('Undo').click();
  assert(await button('Copy image').isDisabled(), 'Outside release commits only once');
  return { passed: checks.length, checks };
}
