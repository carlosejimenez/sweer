// Heavily modified from/inspired by SeeAct
// https://github.com/OSU-NLP-Group/SeeAct/blob/main/seeact_package/seeact/mark_page.js

let labels = [];

window.overlays = {};

var idCounter = new Date().getTime();

function getId(node) {
  // Get an ID of an object. If the object does not have an ID, assign one.
  if (node.id) {
    return node.id;
  } else {
    node.id = "RANDOM_ID_" + idCounter++;
    return node.id;
  }
}

function drawShortcutOverlay(element, labelText) {
  const color = "#" + Math.floor(Math.random() * 16777215).toString(16);

  const newElement = document.createElement("div");
  newElement.style.cssText = `
        outline: 2px dotted ${color};
        position: fixed;
        left: ${element.left}px;
        top: ${element.top}px;
        width: ${element.width}px;
        height: ${element.height}px;
        pointer-events: none;
        box-sizing: border-box;
        z-index: 2147483647;
    `;

  const label = document.createElement("span");
  label.textContent = labelText;

  // Position the label and be careful not to go off the screen
  // default offsets
  let topOffset = -20;
  let leftOffset = 0;
  // handle the case where we are too high up on the screen
  if (element.top < 20) {
    topOffset = 0;
    if (element.left > 20) {
      leftOffset = -20;
    }
  }
  label.style.cssText = `
        position: absolute;
        top: ${topOffset}px;
        left: ${leftOffset}px;
        background: ${color};
        color: white;
        padding: 2px 4px;
        font-size: 12px;
        border-radius: 2px;
    `;
  newElement.appendChild(label);

  document.body.appendChild(newElement);
  labels.push(newElement);
}

overlays.removeShortcutOverlays = function () {
  // Unmark page logic
  for (const label of labels) {
    document.body.removeChild(label);
  }
  labels = [];
};

overlays.drawAllShortcutOverlays = function () {
  overlays.removeShortcutOverlays();

  // Config
  const MINIMUM_ITEM_AREA = 20;
  const INCLUDE_ELEMENTS = [
    "INPUT",
    "TEXTAREA",
    "SELECT",
    "BUTTON",
    "A",
    "IFRAME",
    "VIDEO",
  ];

  let items = Array.from(document.querySelectorAll("*"))
    .map((element) => {
      const vw = Math.max(
        document.documentElement.clientWidth || 0,
        window.innerWidth || 0,
      );
      const vh = Math.max(
        document.documentElement.clientHeight || 0,
        window.innerHeight || 0,
      );
      const textualContent = element.textContent.trim().replace(/\s{2,}/g, " ");
      const elementType = element.tagName.toLowerCase();
      const ariaLabel = element.getAttribute("aria-label") || "";

      const rects = Array.from(element.getClientRects())
        .filter((bb) => {
          const center_x = bb.left + bb.width / 2;
          const center_y = bb.top + bb.height / 2;
          const elAtCenter = document.elementFromPoint(center_x, center_y);
          return elAtCenter === element || element.contains(elAtCenter);
        })
        .map((bb) => {
          const rect = {
            left: Math.max(0, bb.left),
            top: Math.max(0, bb.top),
            right: Math.min(vw, bb.right),
            bottom: Math.min(vh, bb.bottom),
            width: Math.min(vw, bb.right) - Math.max(0, bb.left),
            height: Math.min(vh, bb.bottom) - Math.max(0, bb.top),
          };
          return rect;
        });

      const area = rects.reduce(
        (acc, rect) => acc + rect.width * rect.height,
        0,
      );

      function shouldIncludeElement(element) {
        const tagName = element.tagName;
        const cursorStyle = window.getComputedStyle(element).cursor;
        return (
          INCLUDE_ELEMENTS.includes(tagName) ||
          element.onclick != null ||
          cursorStyle === "pointer"
        );
      }

      return {
        element,
        include: shouldIncludeElement(element),
        area,
        rects,
        text: textualContent,
        type: elementType,
        ariaLabel: ariaLabel,
      };
    })
    .filter((item) => item.include && item.area >= MINIMUM_ITEM_AREA);

  items = items.filter(
    (x) => !items.some((y) => x.element.contains(y.element) && !(x == y)),
  );

  items.forEach((item, index) => {
    item.rects.forEach((bbox) => {
      drawShortcutOverlay(bbox, index);
    });
  });

  const itemInfo = items.flatMap((item, index) => ({
    type: item.type,
    text: item.text,
    id: getId(item.element),
    ariaLabel: item.ariaLabel,
    class: item.element.className,
    label: index.toString(),
  }));

  return itemInfo;
};
