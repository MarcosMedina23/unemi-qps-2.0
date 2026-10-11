@echo off
REM ==========================================================================
REM  UNEMI Guide AI - Compartir la app con un enlace publico (HTTPS).
REM  Doble clic en este archivo. La logica esta en scripts\compartir_enlace.ps1
REM  (-ExecutionPolicy Bypass permite ejecutarlo sin cambiar la configuracion
REM  de seguridad de Windows).
REM ==========================================================================
chcp 65001 >nul
title UNEMI Guide AI - Enlace publico
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\compartir_enlace.ps1"
