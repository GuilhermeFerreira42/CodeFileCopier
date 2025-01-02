@echo off

:: Altere para o diretorio onde o script esta localizado
cd /d %~dp0

:menu
cls
echo Diretorio atual: %cd%
echo =====================================
echo     GIT AUTOMATION MENU
echo =====================================
echo 1. Verificar status do repositorio
echo 2. Adicionar todas as alteracoes
echo 3. Fazer commit
echo 4. Fazer push para o GitHub
echo 5. Fazer pull do repositorio
echo 6. Mostrar log de commits
echo 7. Outras opcoes
echo 8. Sair
echo =====================================
set /p escolha="Escolha uma opcao: "

if %escolha%==1 goto status
if %escolha%==2 goto add
if %escolha%==3 goto commit
if %escolha%==4 goto push
if %escolha%==5 goto pull
if %escolha%==6 goto log
if %escolha%==7 goto outras_opcoes
if %escolha%==8 goto fim
goto menu

:status
echo Diretorio atual: %cd%
echo Verificando o status do repositorio...
git status
pause
goto menu

:add
echo Diretorio atual: %cd%
echo Adicionando todas as alteracoes...
git add .
pause
goto menu

:commit
set /p comentario="Digite o comentario do commit: "
echo Diretorio atual: %cd%
git commit -m "%comentario%"
pause
goto menu

:push
echo Diretorio atual: %cd%
echo Fazendo push para o GitHub...
git push
pause
goto menu

:pull
echo Diretorio atual: %cd%
echo Fazendo pull do repositorio...
git pull
pause
goto menu

:log
echo Diretorio atual: %cd%
echo Mostrando log de commits...
git log
pause
goto menu

:outras_opcoes
cls
echo Outras opcoes
echo =====================================
echo 1. Restaurar arquivos deletados
echo 2. Sincronizar com repositorio
echo 3. Fazer fetch do repositorio
echo 4. Fazer merge de branches
echo 5. Inicializar um novo repositorio
echo 6. Desfazer alteracoes
echo 7. Descartar todas as alteracoes
echo 8. Listar branches
echo 9. Voltar ao menu principal
echo =====================================
set /p escolha_outras="Escolha uma opcao: "

if %escolha_outras%==1 goto restaurar
if %escolha_outras%==2 goto sincronizar
if %escolha_outras%==3 goto fetch
if %escolha_outras%==4 goto merge
if %escolha_outras%==5 goto init
if %escolha_outras%==6 goto reset
if %escolha_outras%==7 goto descartar
if %escolha_outras%==8 goto branch
if %escolha_outras%==9 goto menu
goto outras_opcoes

:restaurar
echo Restaurando arquivos deletados...
git checkout -- .
pause
goto outras_opcoes

:sincronizar
echo Sincronizando com repositorio...
git fetch origin
pause
goto outras_opcoes

:fetch
echo Fazendo fetch do repositorio...
git fetch
pause
goto outras_opcoes

:merge
echo Fazendo merge de branches...
git merge
pause
goto outras_opcoes

:init
echo Inicializando um novo repositorio...
git init
pause
goto outras_opcoes

:descartar
echo Descartando todas as alteracoes...
git checkout .
pause
goto outras_opcoes

:fim
echo Saindo...
pause