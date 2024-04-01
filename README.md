### Install to Ubuntu

1. Install ```menulibre```

    ```
    sudo apt-get install menulibre
    ```

2. Create the ```.desktop``` file for swik and look on the status bar of menulibre to know its name and location

3. Edit ```~/.config/mimeapps.list``` and add the following line:
   ```
   gedit ~/.config/mimeapps.list
   ```
   and add the following line:

   ```
   application/pdf=menulibre-swik.desktop
   ```

4. Update mime list:

   ```
   update-mime-database ~/.local/share/mime
   ```


5. Right click on a PDF file and select ```properties->open with``` and select `swik`
