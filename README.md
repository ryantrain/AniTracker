Welcome to ANITRACKER!

ANITRACKER utilizes Jikan's API to display information and keep track of personal libraries, similar to MyAnimeList and AniList.

In order to set up the environment, please first follow the flask setup tutorial [here](https://flask.palletsprojects.com/en/stable/installation/)

To ensure that the environment was set up correctly, open a new terminal. The terminal should start with "(.venv) PS" and following with your current directory after a short delay.

You may or may not encounter an issue with running third-party scripts on your system. Setting the setting "CurrentUser" to "RemoteSigned" will solve the issue. You can view the permissions list by running "Get-ExecutionPolicy -List" on Windows Powershell.

After setting up the environment, install all the libraries required in requirements.txt by running "pip install [insert library here]" (for examaple "pip install Flask"). After installing every library, you should be good to go!

To run the website, type in "flask --app main run". The site will open [here](http://127.0.0.1:5000). You should open it on your browser for the best experience.

If there are any bugs, please feel free to write them in the issues section!. There is no guaranteed that I will get to them though. Thank you for using ANITRACKER!
