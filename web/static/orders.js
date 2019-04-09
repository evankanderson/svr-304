/**
 * Creates a tree of DOM nodes under an element of type 'type'.
 *
 * Strings become text nodes, and other children are inserted directly
 * (they must be DOM nodes themselves.)
 * @param {string} type
 * @param {object} properties
 * @param {...any} children
 */
function domTree(type, properties, ...children) {
  let domNode = document.createElement(type);
  if (properties) {
    Object.assign(domNode, properties);
  }
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
  let container = document.getElementById("orders");
  for (let e of Array.from(container.childNodes)) {
    e.remove();
  }
  for (let item of data) {
    if (item["items"] == undefined) {
      continue;
    }
    entree_box = domTree("div", { className: "mdc-layout-grid__inner"})
    order = domTree("div", {className: "mdc-layout-grid__cell--span-12" },
        domTree("div", { className: "mdc-card order" },
          domTree("h3", { className: "order-item mdc-typography mdc-typography--headline5" },
            new Date(item.date).toLocaleString("en-US")),
          entree_box,
          domTree('div', {className: "mdc-typography total"},
            'Total: ' + item.totalPrice.toFixed(2))))
    for (let entree of item["items"]) {
      entree_box.appendChild(makeEntree(entree))
    }
    container.appendChild(order)
  }
}

function makeEntree(entree) {
  selections = [];
  console.log(entree)
  for (let category of Object.keys(entree)) {
    if (category == "item") {
      continue;
    }
    for (let selected of entree[category]) {
      selections.push(
        domTree(
          "li",
          { className: "mdc-list-item" },
          domTree("strong", null, category + ": "), selected
        )
      );
    }
  }
  return domTree("div", {className: "mdc-layout-grid__cell--span-6" },
      domTree("div", { className: "mdc-card" },
        domTree("div", { className: "mdc-card__primary-action" },
          domTree("h3", { className: "order-item mdc-typography mdc-typography--headline6" }, entree["item"]),
//          domTree("ul", {className: "mdc-list"}, ...selections)
        )
      
    )
  );
}

function fetchOrders(googleUser) {
  // The ID token you need to pass to your backend:
  var id_token = googleUser.getAuthResponse().id_token;
  // TODO: redirect to order view page
  fetch("/orders", { headers: { Authorization: "Bearer " + id_token } })
    .then(resp => {
      console.log("Got " + resp.status);
      return resp.json();
    })
    .then(data => {
      console.log(data);
      renderOrder(data);
    });
}
