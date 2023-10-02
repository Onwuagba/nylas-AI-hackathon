# LinkLoom
- API to allow users collaborate within email threads by adding annotations aka notes. Users could highlight specific parts of an email, create annotations, leave comments on annotations, and share these annotations with other authorized collaborators. This feature would be valuable for teams working together on projects or handling complex email discussions.


## Getting started
- This project requires python to run locally
- [ ] Clone repo
- [ ] Install dependencies: `pip install requirements.txt`
- [ ] Create a copy of the env file and rename to <b>.env</b>
- [ ] Create a postgres database and include the credentials in the .env file
- [ ] Update .env with Nylas authentication token
- [ ] Update .env with OpenAI authentication key. Get one here: https://openai.com/


## Running project 
-  Once project is completely [setup](#getting-started), simply  run the following command: `python manage.py runserver <port:optional>`
- Import project collection to your API tool (postman, insomnia, etc.) Collection is titled "<b>collections.json</b>"
- [![Run in Insomnia}](https://insomnia.rest/images/run.svg)](https://insomnia.rest/run/?label=LinkLoom%20API&uri=https%3A%2F%2Fgithub.com%2FOnwuagba%2Fnylas-AI-hackathon%2Fblob%2Fdevelop%2Fcollection.json)




