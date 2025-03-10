from fastapi import FastAPI, File, UploadFile, Query, Request
import shutil
import os
import subprocess
import random
import logging
from datetime import datetime
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Diretórios do projeto
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "processed_videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Monta somente o diretório de vídeos processados
app.mount("/processed_videos", StaticFiles(directory=OUTPUT_DIR), name="processed_videos")

# Configuração dos templates: usa a pasta "templates"
templates = Jinja2Templates(directory="templates")

# Caminho do FFmpeg - usa variável de ambiente ou "ffmpeg" por padrão
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")

# Configuração do logger
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.get("/")
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload/")
async def upload_video(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    logger.info(f"📁 Vídeo enviado: {file.filename}")
    return {"mensagem": "✅ Vídeo enviado com sucesso!", "caminho": file_path}


@app.post("/processar/")
async def processar_video(
    filename: str = Query(...),
    intensidade: str = Query("medio"),
    dimensao: str = Query("original"),
    quantidade: int = Query(1)
):
    input_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(input_path):
        logger.error(f"❌ Arquivo não encontrado: {filename}")
        return JSONResponse(content={"erro": "❌ Arquivo não encontrado!"}, status_code=404)
    
    arquivos_processados = []
    erros_processamento = []
    
    for i in range(quantidade):
        # Configuração dos parâmetros conforme a intensidade selecionada
        if intensidade == "leve":
            saturacao = random.uniform(0.9, 1.1)
            brilho = random.uniform(-0.1, 0.1)
            contraste = random.uniform(0.9, 1.1)
            hue = random.uniform(-5, 5)
        elif intensidade == "medio":
            saturacao = random.uniform(0.8, 1.2)
            brilho = random.uniform(-0.15, 0.15)
            contraste = random.uniform(0.85, 1.15)
            hue = random.uniform(-7.5, 7.5)
        else:  # intenso
            saturacao = random.uniform(0.7, 1.3)
            brilho = random.uniform(-0.2, 0.2)
            contraste = random.uniform(0.8, 1.2)
            hue = random.uniform(-10, 10)
        
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        output_filename = f"processed_{filename.split('.')[0]}_v{i+1}_{timestamp}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Monta a cadeia de filtros para o FFmpeg
        filtros = f"eq=saturation={saturacao}:brightness={brilho}:contrast={contraste},hue=h={hue}"
        if dimensao != "original":
            if dimensao == "9:16":
                filtros += ",scale=trunc(ih*9/16/2)*2:ih"
            elif dimensao == "16:9":
                filtros += ",scale=iw:trunc(iw*9/16/2)*2"
                
        comando = [
            FFMPEG_PATH,
            "-y",
            "-i", input_path,
            "-vf", filtros,
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-strict", "experimental",
            "-r", "30",
            output_path
        ]
        
        logger.info(f"🎬 Processando variação {i+1}/{quantidade} do vídeo: {filename}")
        logger.debug(f"Comando FFmpeg: {' '.join(comando)}")
        
        try:
            resultado = subprocess.run(
                comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
            )
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"✅ Variação {i+1} processada: {output_filename}")
                arquivos_processados.append(output_filename)
            else:
                erro_msg = f"Arquivo de saída não criado ou vazio: {output_path}"
                logger.error(f"❌ {erro_msg}")
                erros_processamento.append(erro_msg)
        except subprocess.CalledProcessError as e:
            erro_msg = f"Erro ao processar variação {i+1}. FFmpeg retornou: {e.stderr}"
            logger.error(f"❌ {erro_msg}")
            logger.error(f"Comando: {' '.join(comando)}")
            logger.error(f"Código de retorno: {e.returncode}")
            erros_processamento.append(erro_msg)
    
    if arquivos_processados:
        return {
            "mensagem": f"✅ {len(arquivos_processados)}/{quantidade} variações processadas com sucesso!",
            "arquivos_processados": arquivos_processados
        }
    else:
        return JSONResponse(
            content={
                "erro": "❌ Erro ao processar o vídeo!",
                "detalhes": erros_processamento
            },
            status_code=500
        )


@app.get("/listar-videos/")
async def listar_videos():
    if not os.path.exists(OUTPUT_DIR):
        return JSONResponse(content={"videos": []}, status_code=200)
    arquivos = os.listdir(OUTPUT_DIR)
    if not arquivos:
        return JSONResponse(content={"videos": []}, status_code=200)
    return {"videos": [f"/processed_videos/{arquivo}" for arquivo in arquivos]}


@app.get("/download/{filename}")
async def download_video(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        return JSONResponse(content={"erro": "❌ Arquivo não encontrado!"}, status_code=404)
    return FileResponse(file_path, media_type="video/mp4", filename=filename)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
