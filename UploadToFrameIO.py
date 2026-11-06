import requests
import os
import asyncio
import pip
import httpx
    
os.environ['FRAME_IO_TOKEN'] = ''
os.environ['FRAME_IO_PROJECT_ID'] = ''
os.environ['FRAME_IO_TEAM_ID'] = ''
os.environ['FRAME_IO_ACCOUNT_ID'] = ''
os.environ['FRAME_IO_ASSET_ID'] = ''

async def upload_clip_with_markers(clip, markers):
    video_file = clip.GetClipProperty('File Path')
    video_size = os.path.getsize(video_file)

    split_video_name = video_file.split('/')
    end_of_name = split_video_name[-1]
    name_and_extension = end_of_name.split('.')

    #Step 1: upload the video to frame.io
    #Step 1a: get project details to find root folder ID
    preHeaders = {"Authorization": "Bearer " + os.environ['FRAME_IO_TOKEN']}
    project_resp = requests.get(f'https://api.frame.io/v2/projects/{os.environ['FRAME_IO_PROJECT_ID']}/', headers=preHeaders)

    if project_resp.status_code != 200:
        print('Could not get project details')
        print(project_resp.status_code, project_resp.text)
        exit()

    project_data = project_resp.json()
    root_folder_id = project_data["root_asset_id"]

    #Step 2: get an upload URL under the root folder

    uploadObj = {'filesize': video_size, 'filetype': f'video/{name_and_extension[1]}', 'name': clip.GetName(), 'type': 'file'}
    headers = {"Authorization": "Bearer " + os.environ['FRAME_IO_TOKEN']}
    upload_url_resp = requests.post(f'https://api.frame.io/v2/assets/{root_folder_id}/children', 
                                    headers=headers,
                                    json=uploadObj)

    if upload_url_resp.status_code != 200:
        print('Could not get upload URL')
        print(project_resp.status_code, project_resp.text)
        exit()

    upload_url_data = upload_url_resp.json()
    asset_id = upload_url_data["id"]

    upload_urls = upload_url_data["upload_urls"]

    if upload_urls:
        chunksize = video_size / len(upload_urls)

        current_index = 0

        with open(video_file, 'rb') as f:
            for url in upload_urls:
                if not f:
                    break
                current_index += 1
                print(f"Uploading part {current_index}/{len(upload_urls)}: {url}")
                async with httpx.AsyncClient() as client:
                    part_headers = {"Content-Type" : f"video/{name_and_extension[1]}", "x-amz-acl" : "private"}
                    part_resp = await client.put(url, data=f.read(int(chunksize)), headers=part_headers, timeout=None)
                    print(part_resp.status_code)

                    if part_resp.status_code != 200:
                        print(f'Part {current_index}/{len(upload_urls)} failed to upload.')
                        print(part_resp.status_code, part_resp.text)
                        exit()

    else:
        print("no lol")
        exit()

    print('video uploaded successfully')
    print(f"Asset ID: {asset_id}")

    #Step 2: convert markers on video into comments

    for m in markers:
        markerData = markers[m]
        #We now have the marker data (markers[m]) and its frame [m].
        print("Note: " + str(markers[m]['note']))
        #We now have the comment. Submit this and the frame to the frame.io API
        comment_data = {'text' : str(markers[m]['note']), 'timestamp' : m}
        comment_headers = {"Content-Type" : "application/json", "Authorization" : "Bearer " + os.environ['FRAME_IO_TOKEN']}
        comment_resp = requests.post(f'https://api.frame.io/v2/assets/{asset_id}/comments', headers=comment_headers, json=comment_data)

        response = comment_resp.json()
        print(response)

    #If all has gone according to plan we should now have a video asset with comments on it on frame.io?

#Get important stuff
projectManager = resolve.GetProjectManager()
project = projectManager.GetCurrentProject()
mediaPool = project.GetMediaPool()

#Get target folder
#Get root folder

root_folder = mediaPool.GetCurrentFolder()
clips = root_folder.GetClipList()

#Get markers from active timeline
timeline = project.GetCurrentTimeline()
markers = timeline.GetMarkers()

print('testing script starting')

if not projectManager:
    print("Project manager does not exist")
    exit()

if not project:
    print("Project does not exist")
    exit()

if not mediaPool:
    print("Media pool does not exist")
    exit()

if not root_folder:
    print("Root folder does not exist")
    exit()

if not clips:
    print("Clips does not exist")
    exit()

print("Everything exists")

if len(clips) == 0:
    print(f'No clips in folder {root_folder.GetName()} to transmit')
    exit()

found = False

for clip in clips:
    metadata = clip.GetMetadata('Keywords')
    keywords = str(metadata).split(',')
    #target this clip
    for keyword in keywords:
        if keyword == "frame":
            found = True
            markers = timeline.GetMarkers()
            asyncio.run(upload_clip_with_markers(clip, markers))
            break

if found == False:
    print("No keywords found")
    exit()

