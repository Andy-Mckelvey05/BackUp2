# BackUp v2
### Simular to Backup-v1, changes are:
- Output has changed from a 'preset-date' 7z, file to a directory of the same name, containing a 7z of each inputted path.
- This makes extraction quicker for a slight size trade off.
- This allows me to implement **multi-threading** through concurrency!! meaning the back-up is now created much quicker.
- The display is still through TQDM bars, but now with yellow bars to showcase each threads progress simultaneously.
- Greater input validation and branch confirmation.

## How To Use:
- create a txt file e.g. 'name.txt' and put it in the "Presets" directory.
- fill name.txt with a list with of directory, each line being a new directory
- Run the code, Its advised you run it in terminal as pycharm struggles to display TQDM progress bars.
- After running, you will be prompted with a list of numbers and your presets.
- Input the number of your corresponding preset and press enter.
- Wait for the process to complete ...
- And you're done! The back-up will be in the 'BackUps' directory