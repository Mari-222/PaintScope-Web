// Barra lateral: se expande/contrae y recuerda la preferencia del usuario.
(function () {
  var barra = document.getElementById("sidebar");
  var boton = document.getElementById("sidebar-toggle");
  if (!barra || !boton) return;
  try {
    if (localStorage.getItem("ps-sidebar") === "1") barra.classList.add("sidebar--expanded");
  } catch (e) {}
  boton.addEventListener("click", function () {
    var abierta = barra.classList.toggle("sidebar--expanded");
    try { localStorage.setItem("ps-sidebar", abierta ? "1" : "0"); } catch (e) {}
  });
})();
