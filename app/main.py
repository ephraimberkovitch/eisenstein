from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Response,WebSocket
from fastapi.exceptions import WebSocketRequestValidationError
from fastapi.responses import HTMLResponse, FileResponse
import srsly
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import textract
from pathlib import Path
import spacy
import pymorphy2
#from stanza.pipeline.core import LanguageNotDownloadedError

templates = Jinja2Templates(directory="app/templates")

app = FastAPI()
app.mount("/assets", StaticFiles(directory="./app/assets"), name="assets")

# Session variables
texts = []
language_select = None
lemmatized_text = None 
tesseract_languages = srsly.read_json("./app/tesseract_languages.json")
tesseract_stanza = srsly.read_json("./app/tesseract_to_stanza_codes.json")
#has_stanza = [a[0] for a in tesseract_stanza.items()] Until I can get stanza to behave
has_stanza = ['rus']
# Routes 
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "languages":tesseract_languages, "has_stanza":has_stanza})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        print(data)
        html_content = """"""
        for text in texts:
            html_content += f"""
                
                <div class="col-md-6 col-lg-3 d-flex align-items-stretch mb-5 mb-lg-0" data-aos="fade-up" data-aos-delay="100">
                <div class="icon-box">
                <h4 class="title"><a href="">{text['filename']}</a></h4>
                <p>{text['file_type']}</p>
                <p class="description">{text['text'][:500]}</p>
                <div class="icon"><i onclick="download('{text['filename']}');" class="bx bx-download"></i></div>

                </div>
            </div>

    
        """

        await websocket.send_text(html_content)

@app.get("/texts", response_class=HTMLResponse)
async def get_texts(current_texts:str = None):
    #if entries in texts not in current_texts, delete them 
    #This will keep dict in sync with browser
    
    html_content = """"""
    for text in texts:
        html_content += f"""
            
            <div class="col-md-6 col-lg-3 d-flex align-items-stretch mb-5 mb-lg-0" data-aos="fade-up" data-aos-delay="100">
            <div class="icon-box">
              <h4 class="title"><a href="">{text['filename']}</a></h4>
              <p>{text['file_type']}</p>
              <p class="description">{text['text'][:500]}</p>
              <div class="icon"><i onclick="download('{text['filename']}');" class="bx bx-download"></i></div>

            </div>
          </div>

   
    """
    return HTMLResponse(content=html_content, status_code=200)


def process_with_language(temp_file:str,language_select:str) -> str:
    try:
        text = textract.process(temp_file, language=language_select)
        return text
    except Exception as e:
        return Response(content=str(e), status_code=500)
     

@app.post("/uploadfiles")
def save_texts(file: UploadFile = File(...),language_select:str= Form(...), lemmatized_text:str= Form(...)):
    print(lemmatized_text, language_select)
    contents = file.file.read()
    temp_file = Path(f'/tmp/{file.filename}')
    temp_file.write_bytes(contents)
 
    text= process_with_language(temp_file,language_select)
    text = text.decode('utf-8')
    if lemmatized_text == 'true':
        
        if language_select == 'rus':
            lemmatizer = pymorphy2.MorphAnalyzer()
            from spacy.lang.ru import Russian
            nlp = Russian()

            doc = nlp(text)
            p = [lemmatizer.parse(token.text)[0].normal_form for token in doc if not token.is_stop and not token.is_punct]
            text = ' '.join([i for i in p])
        
    temp_file.unlink() # Delete file from system
    texts.append({"filename": file.filename, "file_type": file.content_type, "text":text})
    return file.filename

@app.get("/download")
async def download(filename:str = None):
    text = [a for a in texts if a['filename'] == filename]
    if len(text) == 1:
        text = text[0]
        #{'filename': 'NEH-Preferred-Seal820.jpg', 'file_type': 'image/jpeg', 'text': 'NATIONAL\nENDOWMENT\nFOR THE\nHUMANITIES\n\n \n\x0c'}
        temp_file = Path('/tmp/'+ text['filename'])
        print(text['text'])
        temp_file.write_text(text['text'])
        new_name = text['filename'].split('.')[0] +".txt"
        return FileResponse(temp_file, media_type=text['file_type'], filename=new_name)

    else:
        print('error')
        raise HTTPException(status_code=404, detail=f"Item {filename} not found")
