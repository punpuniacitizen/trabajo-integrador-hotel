@echo off
rem Abre la guia de estudio y el mapa del codigo en el navegador (no necesita internet ni el servidor).
cd /d "%~dp0"
start "" "docs\guia-de-estudio.html"
start "" "docs\mapa-del-codigo.html"
