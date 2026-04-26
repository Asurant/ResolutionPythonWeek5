from browser import document, html, aio
import json

from browser.local_storage import storage
storage['foo'] = 'bar'
print(storage['foo'])

api_key = None

if "api_key" in storage:
    api_key = storage["api_key"]

def register(event):
    name = document["name-input"].value
    async def registerKey():
        global api_key
        req = await aio.post(
            "/register",
            headers = {
                "Content-Type": "application/json"
            },
            data = json.dumps({"name": name})
        )

        if req.status == 200:
            data = json.loads(req.data)
            storage["api_key"] = data["api_key"]

            api_key = data["api_key"]
            await load_items()
        
        print(storage.get("api_key"))
        
    aio.run(registerKey())

document["registerButton"].bind("click", register)

flashcardsList = html.DIV()
async def load_items():
    flashcardsList.clear()
    req = await aio.get("/flashcards", headers={"x-api-key": api_key})

    if req.status == 200:
        flashcards = json.loads(req.data)
        for flashcard in flashcards:
            card = html.DIV()
            text = html.P(f"{flashcard['question']} --> {flashcard['answer']}")
            deleteButton = html.BUTTON("Delete")
            def delete(flashcard_id):
                def deleteClick(event):
                    async def deleteItem():
                        req = await aio.ajax("DELETE", f"/flashcards/{flashcard_id}", headers = {"x-api-key": api_key})
                        if req.status == 200:
                            print("Deleted")
                        await load_items()
                    aio.run(deleteItem())
                return deleteClick
            
            deleteButton.bind("click", delete(flashcard["id"]))
            card.appendChild(text)
            card.appendChild(deleteButton)
            flashcardsList.appendChild(card)
    else:
        print(f"Error: {req.status}")

categoryInput = html.INPUT(placeholder="Category")
questionInput = html.INPUT(placeholder="Question")
answerInput = html.INPUT(placeholder="Answer")
addButton = html.BUTTON("Add Flashcard")

def addFlashcard(event):
    async def actuallyAddFlashcard():
        await aio.post(
            "/flashcards",
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json"
            },
            data = json.dumps({
                "category": categoryInput.value,
                "question": questionInput.value,
                "answer": answerInput.value})
            )
        await load_items()
    aio.run(actuallyAddFlashcard())

addButton.bind("click", addFlashcard)

darkMode = False

def lightDarkToggle(event):
    global darkMode
    body = document["body"]
    if darkMode:
        body.style.backgroundColor = "white"
        body.style.color = "black"
        darkMode = False
    else:
        body.style.backgroundColor = "#303030"
        body.style.color = "white"
        darkMode = True

document["LightDarkButton"].bind("click", lightDarkToggle)

document["app"].appendChild(categoryInput)
document["app"].appendChild(questionInput)
document["app"].appendChild(answerInput)
document["app"].appendChild(addButton)
document["app"].appendChild(html.HR())
document["app"].appendChild(flashcardsList)

if api_key:
    aio.run(load_items())