// Run with playwright-cli run-code after opening the local sketchpad.
// All drawings here are test fixtures, never user references or approvals.
async (page) => {
  const checks = [];
  const assert = (condition, label) => {
    if (!condition) throw new Error(label);
    checks.push(label);
  };
  const button = (name) => page.getByRole("button", { name, exact: true });
  const canvas = page.getByLabel(
    "Drawing canvas. Draw with a mouse, finger, or stylus.",
    { exact: true },
  );
  const pixel = (x, y) =>
    canvas.evaluate(
      (el, [x, y]) => Array.from(el.getContext("2d").getImageData(
        Math.min(el.width - 1, Math.round(x * el.width / 1200)),
        Math.min(el.height - 1, Math.round(y * el.height / 900)), 1, 1).data),
      [x, y],
    );
  const equals = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const white = [255, 255, 255, 255];
  const charcoal = [37, 41, 51, 255];
  const blue = [75, 92, 219, 255];
  const draw = async (points) => {
    await canvas.scrollIntoViewIfNeeded();
    const rect = await canvas.boundingBox();
    const [first, ...rest] = points;
    await page.mouse.move(
      rect.x + (first[0] * rect.width) / 1200,
      rect.y + (first[1] * rect.height) / 900,
    );
    await page.mouse.down();
    for (const p of rest)
      await page.mouse.move(
        rect.x + (p[0] * rect.width) / 1200,
        rect.y + (p[1] * rect.height) / 900,
        { steps: 8 },
      );
    await page.mouse.up();
  };
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1280, height: 1040 });
  await page.reload();
  assert(
    await button("Copy image").isDisabled(),
    "Blank canvas cannot be copied",
  );
  assert(equals(await pixel(300, 100), white), "Canvas starts opaque white");
  await draw([
    [100, 100],
    [500, 100],
  ]);
  assert(
    equals(await pixel(300, 100), charcoal),
    "Mouse draws at scaled canvas coordinates",
  );
  await button("Undo").click();
  assert(equals(await pixel(300, 100), white), "Undo removes the stroke");
  await button("Redo").click();
  assert(equals(await pixel(300, 100), charcoal), "Redo restores the stroke");
  await button("Eraser").click();
  await draw([[300, 100]]);
  assert(
    equals(await pixel(300, 100), white),
    "Eraser removes ink on opaque white",
  );
  await button("Undo").click();
  assert(equals(await pixel(300, 100), charcoal), "Undo restores erased ink");
  await button("Blue").click();
  assert(
    (await button("Pen").getAttribute("aria-pressed")) === "true",
    "Choosing ink exits eraser mode",
  );
  await button("Line").click();
  await draw([
    [100, 220],
    [500, 220],
  ]);
  assert(equals(await pixel(300, 220), blue), "Line uses the selected color");
  await button("Rectangle").click();
  await draw([
    [600, 100],
    [900, 300],
  ]);
  assert(
    equals(await pixel(600, 200), blue) && equals(await pixel(700, 200), white),
    "Rectangle draws an unfilled outline",
  );
  await button("Ellipse").click();
  await draw([
    [650, 400],
    [950, 600],
  ]);
  assert(equals(await pixel(950, 500), blue), "Ellipse draws an outline");
  const beforeClear = await canvas.evaluate((el) => el.toDataURL());
  await button("Clear").click();
  assert(
    equals(await pixel(600, 200), white) &&
      (await button("Copy image").isDisabled()),
    "Clear resets the paper and export controls",
  );
  await button("Undo").click();
  assert(
    (await canvas.evaluate((el) => el.toDataURL())) === beforeClear,
    "Undo clear restores the entire reference exactly",
  );

  // Exercise the real PNG encoding and ClipboardItem, substituting only the OS writer.
  await page.evaluate(() => {
    Object.defineProperty(navigator.clipboard, "write", {
      configurable: true,
      value: async (items) => {
        const activated = navigator.userActivation.isActive;
        const blob = await items[0].getType("image/png");
        const image = await createImageBitmap(blob);
        const output = document.createElement("canvas");
        output.width = image.width;
        output.height = image.height;
        output.getContext("2d").drawImage(image, 0, 0);
        window.__sketchTestCopy = {
          activated,
          type: blob.type,
          width: image.width,
          height: image.height,
          exact:
            output.toDataURL() === document.querySelector("canvas").toDataURL(),
        };
        image.close();
      },
    });
  });
  await button("Copy image").click();
  await page.waitForFunction(() => window.__sketchTestCopy);
  const copied = await page.evaluate(() => window.__sketchTestCopy);
  const dimensions = await canvas.evaluate(el => ({width:el.width,height:el.height}));
  assert(copied.activated, "Clipboard write starts during the user click");
  assert(
    copied.type === "image/png" &&
      copied.width === dimensions.width &&
      copied.height === dimensions.height,
    "Clipboard receives a full-resolution PNG",
  );
  assert(
    copied.exact,
    "Copied PNG exactly matches the paper without UI or hints",
  );
  assert(
    (await page.locator("#status").textContent()).includes(
      "Image copied!",
    ),
    "Copy reports success after the writer resolves",
  );
  await page.evaluate(() =>
    Object.defineProperty(navigator.clipboard, "write", {
      configurable: true,
      value: async () => {
        throw new DOMException("Test denial", "NotAllowedError");
      },
    }),
  );
  await button("Copy image").click();
  assert(
    (await page.locator("#status").textContent()).includes(
      "Copy was blocked",
    ),
    "Clipboard denial offers a download fallback",
  );
  const downloading = page.waitForEvent("download");
  await button("Download PNG").click();
  const download = await downloading;
  await download.saveAs("output/playwright/canvas2imagegen-fixture.png");
  assert(
    (await download.failure()) === null &&
      download.suggestedFilename().endsWith(".png"),
    "PNG download succeeds after clipboard denial",
  );
  await page.evaluate(() =>
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: undefined,
    }),
  );
  await button("Copy image").click();
  assert(
    (await page.locator("#status").textContent()).includes(
      "Download PNG",
    ),
    "Unsupported clipboard API offers a download fallback",
  );
  await page.screenshot({
    path: "output/playwright/canvas2imagegen-desktop.png",
    fullPage: true,
  });

  await page.setViewportSize({ width: 390, height: 844 });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    "Mobile layout fits without horizontal scrolling",
  );
  await button("Pen").click();
  await draw([
    [200, 700],
    [600, 700],
  ]);
  assert(
    equals(await pixel(400, 700), blue),
    "Drawing stays aligned after responsive resize",
  );
  await page.screenshot({
    path: "output/playwright/canvas2imagegen-mobile.png",
    fullPage: true,
  });
  await page.keyboard.press("Control+z");
  assert(
    equals(await pixel(400, 700), white),
    "Keyboard undo restores the previous image",
  );
  await page.keyboard.press("Control+Shift+z");
  assert(
    equals(await pixel(400, 700), blue),
    "Keyboard redo restores the stroke",
  );

  await page.setViewportSize({ width: 1280, height: 720 });
  await page.reload();
  const shortCanvas = await canvas.boundingBox();
  assert(
    shortCanvas.y >= 0 && shortCanvas.y + shortCanvas.height <= 720,
    "Whole canvas fits a short desktop window",
  );
  await page.screenshot({
    path: "output/playwright/canvas2imagegen-compact.png",
    fullPage: true,
  });

  // Browser-native touch and clipboard checks use only this fixture page.
  const session = await page.context().newCDPSession(page);
  const tx = shortCanvas.x + shortCanvas.width / 4;
  const ty = shortCanvas.y + shortCanvas.height / 2;
  await session.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ x: tx, y: ty }],
  });
  await session.send("Input.dispatchTouchEvent", {
    type: "touchMove",
    touchPoints: [{ x: tx + shortCanvas.width / 4, y: ty }],
  });
  await session.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [],
  });
  assert(
    equals(await pixel(450, 450), charcoal),
    "Touch input creates an aligned stroke",
  );
  await session.detach();
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
  await button("Copy image").click();
  await page.waitForFunction(() => document.getElementById("status").textContent.includes("Image copied!"));
  assert(
    (await page.locator("#status").textContent()).includes(
      "Image copied!",
    ),
    "Native browser clipboard write succeeds",
  );
  const nativeCopy = await page.evaluate(async () => {
    const items = await navigator.clipboard.read();
    const blob = await items[0].getType("image/png");
    const bitmap = await createImageBitmap(blob);
    const output = document.createElement("canvas");
    output.width = bitmap.width;
    output.height = bitmap.height;
    output.getContext("2d").drawImage(bitmap, 0, 0);
    bitmap.close();
    return output.toDataURL() === document.querySelector("canvas").toDataURL();
  });
  assert(
    nativeCopy,
    "Native clipboard contains the exact test drawing as a PNG",
  );
  assert(errors.length === 0, "No browser runtime errors");
  return { passed: checks.length, checks, copied };
}
