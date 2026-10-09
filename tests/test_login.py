def test_la_administracion_pide_login(anonimo):
    respuesta = anonimo.get("/administracion/?fecha=2026-10-14")
    assert respuesta.status_code == 302
    assert "/administracion/login?next=" in respuesta.location


def test_la_api_sin_login_devuelve_401(anonimo, habitacion):
    respuesta = anonimo.post(f"/administracion/api/habitaciones/{habitacion.id}/limpieza", json={"estado": "sucia"})
    assert respuesta.status_code == 401


def test_login_correcto_vuelve_a_la_pagina_pedida(anonimo, usuario):
    respuesta = anonimo.post(
        "/administracion/login?next=/administracion/?fecha=2026-10-14",
        data={"email": "SOFIA@hotel.test", "password": "clave-de-prueba"},
    )
    assert respuesta.status_code == 302
    assert respuesta.location == "/administracion/?fecha=2026-10-14"
    assert anonimo.get("/administracion/").status_code == 200


def test_login_con_contrasena_incorrecta(anonimo, usuario):
    respuesta = anonimo.post("/administracion/login", data={"email": "sofia@hotel.test", "password": "otra"})
    assert respuesta.status_code == 401
    assert "no son correctos" in respuesta.get_data(as_text=True)


def test_login_no_redirige_a_otro_sitio(anonimo, usuario):
    respuesta = anonimo.post(
        "/administracion/login?next=//sitio-malo.example",
        data={"email": "sofia@hotel.test", "password": "clave-de-prueba"},
    )
    assert respuesta.location == "/administracion/"


def test_logout(cliente):
    cliente.post("/administracion/logout")
    assert cliente.get("/administracion/").status_code == 302
