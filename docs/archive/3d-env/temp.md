Please make sure that the other project:job-finder-claude is not broken don't move MCPS or other functionality make sure it will stay working I am still using it and need it I am trying to see if I can optimize here and have another project until it is clearly proved better I need project to work don't make it to not brake:
    - /mnt/c/Users/vardana/Documents/Proj/job-finder-claude/


Is this going to work, linkedin can search with or pattern correctly  ?
 - LinkedIn: 1 combined search only (all titles OR'd together). No description fetch.

Is there any big risk of not seeing jobs we look for because we used this OR approach ?

----

 - RemoteHunter: WebSearch with top terms from the title list. ?
Again, I need to search for oll the job titles in all platforms. don't want to skip something depending on platform, don't want to miss some job search in any job platform.

----

Please write a good example with current setup of: input/search-config.md 
I will review and change if needed, thank you!

----

Again, do we really sure this will work ?
 2. LinkedIn search (1 call): join all titles with OR → "EDA QA Engineer" OR "SDET" OR 

----
My assumption is that we should search for each job title from the preferred job titles list provided as input, but is the: (1 call) or (2 calls) mentioned below do the same work ?:
 2. LinkedIn search (1 call): join all titles with OR → "EDA QA Engineer" OR "SDET" OR "Software Engineer in Test" OR ...
 3. Glassdoor searches (2 calls): split titles into EDA-focused group + broad QA group



1. Please indroduce GPS coordinates 


I would like to have the terrain map as a separate file. Not script but something which should or could be loaded everywhere for example in this 3d-env and gcs_server and other applications in future we may build. 
We already use Json and put it under /mnt/c/Users/vardana/Documents/Proj/remote-rover/config/terrain_scene.json but it seems not full. 
I want to have all the objects there so in the GCS-server when I need to have a map of the terrain it should read from the same source from this same config so it can clearly reconstruct from the same source if it needs to evaluate some script to create all objects I would like it to be done once. Whenever I create some layout for all the objects I can see in the terrain during driving the rover or when the map is shown for all the objects in config file it should have its corresponding text(jsonl ?) description not evaluating to create random or some loops or other scripts but for each object a text a json line.  If we have some loops for randomly creating objects it can be used in some pipeline to create the final json file containing all the final evaluated objects that weill present in the tarrain. The same json (jsonl ?) files then terrain Python loads it for the 3DNA and GCS server loads it for for for the map or there will be other logic using the terrain assuming all the objects
  are already there and it can have access to it with their coordinates Later I will need coordinates so I will process the terrain object to construct some maps not maps but routings for the rover or
  other functionality



if the generator here needs separate execution, please check that we have how to run document for each sub projects here in this remote rover for example for GCS server for 3d-env and for this generator as well what else needs to be there 
Additionally, please clean up documents, review and remove all the things which already modified and don't correspond to the current project and update documentation. Then you can remove files if needed, but please ask before and mention why you think it should be removed. I believe there will be need some cleanup for this project already, but I'm trying to be careful. Please also check that if it really needs some cleanup, but don't spend too much tokens on that.



now let's see how fast how fast you will convert this speech to test I will speak probably will try to speak couple of minutes let's see how you will behave here with this last prompt I try to achieve that all the hard coded objects which should be in terrain should be isolated to from the code so it can be read from multiple places particularly when running simulator and when running GCS server the terrain and all the objects should be loaded in the map also there will be autopilot which will see all the objects in the map and also there will be autopilot which will see all the objects in the map and also there will be autopilot which will see all the objects in the map and also there will be autopilot which will see all the objects in the map and also there will be autopilot which will see all the objects in the map and also there will be autopilot which will see all the objects in the map and also there will be autopilot which will see all the objects in the map and also there will be autopilot which will see all the objects in the map and also there will be autopilot which will see all the objects and may do its autopiloting things defining routings avoiding obstacles and managing the rover drive so this is the main idea to have all the 3d objects a terrain map and all the objects isolated so 3d sim environment will read it gcs server will read it to show on the map and autopilot based on llm or other approaches should see it now let's see how much time this transcription will take


Now please check I believe this newly created terrain extracted file in the config can be used to construct the map in the GCS server replay page. I need to see terrain map in the GCS server replay page. So when we record and replay or play the rover movements the rover can be seen on the map according to replay. Please check if this map import from the generated terrain ASCII files to construct the maps on the GCS server replay page. If it's not implemented, please plan for implementation.

Now the replay page seems broken. It should record the rover's telemetry data, especially GPS coordinates, positions, and should put the rover on the map and replay the rover movement on the map. The map should be constructed from the config file, pre-generated scene file in the config. Please make sure this works. I need to record rover movement on the terrain and be able to replay these recordings. To see in past how the rover was moving, where to move it, etc. To see in past how the rover was moving, where to move it, etc. It is showing currently my city, which is not correct. It should be this virtual 3D-env map.
