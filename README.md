NESI - Nova Echo Science & Industry
=====

A single window application to display the status of science and industrial jobs in the game 'Eve Online' by CCP Games.
Users provide API key credentials to use with the CCP servers to download data from the the corporate and character industry jobs API.

The API key the user provides can be a personal key with at least Industry access or a corporation key with the role 'Factory Manager' or above access
otherwise the API server will return HTTP 403 errors - Access Denied.
Support for the use of multiple API keys, all returning data to a single list of current jobs.

Implementation of sqlite access to reduced copy of CCP static data dump for conversion of API supplied values to human readable format, and reduced network usage due to moving away from using the API server for this function.
I am working to futher reduce the data set from the static data dump for this application to reduce its footprint.

POS (Player Owned Structures) status details from API (Requires a corporate key with at least Fuel Technician role), showing state, fuel quantity and time remaining for fuels of listed towers.

Manufacturing calculator added using data from static data dump as per request from corporation member.

The application generates a set of local cache files within its directory to reduce network data, and saves the user details in nesi.ini file.

This project uses wxPython, sqlite3 and ObjectListView modules.
