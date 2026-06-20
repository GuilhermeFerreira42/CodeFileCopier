#!/bin/bash

function show_menu() {
    clear
    echo "Diretório atual: $(pwd)"
    echo "====================================="
    echo "      GIT AUTOMATION MENU (LINUX)"
    echo "====================================="
    echo "1. Verificar status do repositório (git status)"
    echo "2. Adicionar todas as alterações (git add .)"
    echo "3. Adicionar e Comitar (git add . && git commit)"
    echo "4. Fazer commit (git commit)"
    echo "5. Fazer push para o GitHub (git push)"
    echo "6. Fazer pull do repositório (git pull)"
    echo "7. Mostrar log de commits (git log)"
    echo "8. Obter link do projeto (git remote -v)"
    echo "9. Outras opções"
    echo "0. Sair"
    echo "====================================="
    read -p "Escolha uma opção: " escolha
}

function pause() {
    read -p "Pressione [Enter] para continuar..."
}

while true; do
    show_menu
    case $escolha in
        1) git status; pause ;;
        2) git add .; echo "Alterações adicionadas."; pause ;;
        3) read -p "Mensagem do commit: " msg; git add .; git commit -m "$msg"; pause ;;
        4) git commit; pause ;;
        5) git push; pause ;;
        6) git pull; pause ;;
        7) git log --oneline --graph --all; pause ;;
        8) git remote -v; pause ;;
        9) 
            while true; do
                clear
                echo "OUTRAS OPÇÕES"
                echo "======================================================="
                echo "1. Restaurar arquivos (git restore .)"
                echo "2. Sincronizar (git fetch origin)"
                echo "3. Merge de branch"
                echo "4. Inicializar repositório (git init)"
                echo "5. Listar branches (git branch -a)"
                echo "0. Voltar ao menu principal"
                read -p "Escolha uma opção: " opt_outras
                case $opt_outras in
                    1) git restore .; echo "Arquivos restaurados."; pause ;;
                    2) git fetch origin; pause ;;
                    3) read -p "Nome da branch: " br; git merge $br; pause ;;
                    4) git init; pause ;;
                    5) git branch -a; pause ;;
                    0) break ;;
                esac
            done
            ;;
        0) exit 0 ;;
        *) echo "Opção inválida"; pause ;;
    esac
done
