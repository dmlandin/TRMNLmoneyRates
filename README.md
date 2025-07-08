# TRMNLmoneyRates
Making a plugin for TRMNL e-ink display with custom fields from 
-St. Louis Federal Reserve FRED data
-Chatham Finanical quarterly CRE market spreads data (email distribution list - some manual setup and local extraction needed here but the request for the PDF is free from Chatham Financial website https://www.chathamfinancial.com/insights/)

More Details:
![image](https://github.com/user-attachments/assets/9e309a69-3483-441b-be52-94584e568ba2)
TRMNL (https://usetrmnl.com/) is a low power e-ink display for persistant data and infrequent updates.  There are pre-set plugins for system integrations (google, microsoft, etc) but also the ability to create custome plugins.  This specific plugin is for financial real estate developers.
There are two main features:
1) A persistant script to run via GitHub Actions (or any others service) to poll the St. Lous FRED data and output a JSON file for TRMNL backend to read.
2) An manual run, intermitten script to identify the latest Chatham Financial report (that the user manually saves into the project directly quarterly), search for the market keyword desired (currently set to medical) and publish those spreads in a JSON file

TRMNL then polls both JSON and displays that data -> the TRMNL markup.html is NOT USED by TRMNL.  TRMNL has a specific view and edit markup window to create the page.  The file in this repo is simply a copy/backup.  
