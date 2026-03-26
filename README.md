# Agent Based Modelling (ABM) in Financial Flash Crashes

This is a university project as part of the (King's College London) MSc Computational Finance course.


## How to run visual simulation dashboard
Ensure that you are in the source directory for the codebase via: <br>
`cd "ABM Project/src"`
<br>
From here ensure that the Solara library is installed. Once installed you can now run the dashboard via: <br>
`Solara run app.py`
<br>
From here the app should appear as a new tab within your browser.

## How to run our experiment with output graphs
It is easier to open up the `ABM Project` directory within a code IDE of your chosing. From here go to:<br>
`src/Analysis`<br>
Then run the `Runner.py` file. With our hardware we were able to run the experiment within 15 minutes, however the time it takes may vary based on your processor. Once complete the outputted csv tables are store in the `Data` folder. <br>
Note that we have already included our outputs, so simply re-runnning the experiment will overwrite them. Feel free to look through the tables. To generate the graphs (existing ones already included) you can run the `Plot.py` file which will read the csv tables and ouput a series of graphs in the `Graphs` folder.
