# realiza o download da ultima versao de imagem python disponivel no docker hub
FROM python:latest

# copia arquivo de dependencias
COPY requirements.txt /tmp/requirements.txt

# instalando as dependencias python
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# criando diretorio de trabalho onde serao guardados os arquivos dos servicos
RUN mkdir /servico
WORKDIR /servico
