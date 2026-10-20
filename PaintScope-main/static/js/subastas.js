// PaintScope · cuentas regresivas, actualización en vivo (cada 2 s) y confirmación de puja.
(function () {
  "use strict";

  function dinero(n) {
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  }

  function formatoTiempo(seg) {
    if (seg <= 0) return "Cerrando…";
    var d = Math.floor(seg / 86400), h = Math.floor((seg % 86400) / 3600),
        m = Math.floor((seg % 3600) / 60), s = seg % 60;
    var dos = function (x) { return (x < 10 ? "0" : "") + x; };
    if (d > 0) return dos(d) + "d " + dos(h) + "h";
    if (h > 0) return dos(h) + "h " + dos(m) + "m";
    return dos(m) + "m " + dos(s) + "s";
  }

  // --- Cuenta regresiva: cada elemento .js-timer lleva data-restante en segundos
  function pintarTimers() {
    document.querySelectorAll(".js-timer").forEach(function (el) {
      var r = parseInt(el.getAttribute("data-restante"), 10);
      if (isNaN(r)) return;
      el.textContent = formatoTiempo(r);
    });
  }
  function tick() {
    document.querySelectorAll(".js-timer").forEach(function (el) {
      var r = parseInt(el.getAttribute("data-restante"), 10);
      if (!isNaN(r) && r > 0) el.setAttribute("data-restante", r - 1);
    });
    pintarTimers();
  }
  pintarTimers();
  setInterval(tick, 1000);

  // --- Actualiza una tarjeta o fila con los datos del servidor
  function aplicar(contenedor, datos) {
    var precio = contenedor.querySelectorAll(".js-precio");
    var pujas = contenedor.querySelectorAll(".js-pujas");
    var nuevo = dinero(datos.precio);
    var cambio = false;
    precio.forEach(function (el) {
      if (el.textContent !== nuevo) { el.textContent = nuevo; cambio = true; }
    });
    pujas.forEach(function (el) { el.textContent = datos.pujas; });
    contenedor.querySelectorAll(".js-timer").forEach(function (el) {
      el.setAttribute("data-restante", datos.segundos);
    });
    if (cambio) {
      var tarjeta = contenedor.closest("[data-subasta]") || contenedor;
      tarjeta.classList.remove("flash");
      void tarjeta.offsetWidth;
      tarjeta.classList.add("flash");
    }
    return cambio;
  }

  // --- Dashboard de subastas activas (RF-08, RNF-03)
  var dash = document.querySelector('[data-poll="dashboard"]');
  if (dash) {
    var urlDash = dash.getAttribute("data-url");
    setInterval(function () {
      fetch(urlDash, { credentials: "same-origin", headers: { Accept: "application/json" } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (json) {
          if (!json) return;
          var enPantalla = Array.prototype.map.call(dash.querySelectorAll("[data-subasta]"),
            function (n) { return n.getAttribute("data-subasta"); }).sort().join(",");
          var enServidor = json.subastas.map(function (s) { return String(s.id); }).sort().join(",");
          if (enPantalla !== enServidor) { window.location.reload(); return; }
          json.subastas.forEach(function (s) {
            var fila = dash.querySelector('[data-subasta="' + s.id + '"]');
            if (fila) aplicar(fila, s);
          });
        })
        .catch(function () { /* sin red: se reintenta en el siguiente ciclo */ });
    }, 2000);
  }

  // --- Detalle de una subasta
  var det = document.querySelector('[data-poll="detalle"]');
  if (det && det.getAttribute("data-estado") !== "cerrada") {
    var urlDet = det.getAttribute("data-url");
    setInterval(function () {
      fetch(urlDet, { credentials: "same-origin", headers: { Accept: "application/json" } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (s) {
          if (!s) return;
          if (s.estado !== det.getAttribute("data-estado")) { window.location.reload(); return; }
          aplicar(det, s);
          var ext = det.querySelector(".js-extension");
          if (ext && s.extensiones > 0) {
            ext.hidden = false;
            var n = ext.querySelector(".js-ext-n");
            if (n) n.textContent = s.extensiones;
          }
          var entrada = document.getElementById("bid-monto");
          if (entrada) entrada.min = Math.floor(s.precio) + 1;
        })
        .catch(function () {});
    }, 2000);
  }

  // --- Formulario de puja: botones +/- y confirmación antes de enviar
  var form = document.getElementById("bid-form");
  if (form) {
    var monto = document.getElementById("bid-monto");
    var minimo = function () { return parseInt(monto.min, 10) || 0; };
    document.getElementById("bid-plus").addEventListener("click", function () {
      monto.value = (parseInt(monto.value, 10) || minimo()) + 10;
    });
    document.getElementById("bid-minus").addEventListener("click", function () {
      monto.value = Math.max(minimo(), (parseInt(monto.value, 10) || minimo()) - 10);
    });
    var dialogo = document.getElementById("bid-dialog");
    if (dialogo && typeof dialogo.showModal === "function") {
      var confirmado = false;
      form.addEventListener("submit", function (e) {
        if (confirmado) return;
        e.preventDefault();
        if (!form.reportValidity()) return;
        document.getElementById("bid-dialog-monto").textContent = dinero(parseInt(monto.value, 10));
        dialogo.showModal();
      });
      document.getElementById("bid-confirm").addEventListener("click", function () {
        confirmado = true; dialogo.close(); form.submit();
      });
      document.getElementById("bid-cancel").addEventListener("click", function () { dialogo.close(); });
    }
  }
})();
