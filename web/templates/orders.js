/**
 * Creates a tree of DOM nodes under an element of type 'type'.
 *
 * Strings become text nodes, and other children are inserted directly
 * (they must be DOM nodes themselves.)
 * @param {string} type
 * @param {...any} children
 */
function domTree(type, ...children) {
  let domNode = document.createElement(type);
  for (let child of children) {
    if (typeof child == "string") {
      child = document.createTextNode(child);
    }
    domNode.appendChild(child);
  }
  return domNode;
}

/**
 * Render order data into the "order" element in the document.
 * @param {*} data
 */
function renderOrder(data) {
  let container = document.getElementById("order");
  for (let e of Array.from(container.childNodes)) {
    e.remove();
  }
  for (let item of data) {
    let list = domNode("ul");
    for (let entree of item["items"]) {
      list.appendChild(domNode("li", domNode("h3", entree["item"])));
    }
    container.appendChild(domNode("div", domNode("h2", item["id"], list)));
  }
}
