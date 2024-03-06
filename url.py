#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint

import websocket #pip install websocket-client NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
from PIL import Image, ImageDraw
server_address = "192.169.170.63:9000" #pbox comfyui服务器的地址
client_id = str(uuid.uuid4())

def queue_prompt(prompt): #提交生成任务 uuid生成本次websocket连接的client id 识别客户端的唯一标识符。通过在连接URL中传递client_id，服务器可以识别不同的客户端并根据其需要进行个性化的操作或处理。这种方法也可以用于身份验证或其他目的。
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read()) # 不会返回本次生成的图结果 只会返回本次任务的ID和任务序号数字 以及报错信息 ex: {'prompt_id': '4b25f6ca-3dc0-41b6-8177-de694bcf8a91', 'number': 49, 'node_errors': {}}

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
    # 请求图片 http://192.169.170.63:9000/view?filename=ComfyUI_01033_.png&subfolder=&type=output
        return response.read()
        # 拿到16进制的图像数据
def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())
    #{'79aa60c3-d8e1-4c3b-afa8-45067b0c0225': {'prompt': [50, '79aa60c3-d8e1-4c3b-afa8-45067b0c0225', {'3': {'inputs': {'seed': 5, 'steps': 20, 'cfg': 8.0, 'sampler_name': 'euler', 'scheduler': 'normal', 'denoise': 1.0, 'model': ['4', 0], 'positive': ['6', 0], 'negative': ['7', 0], 'latent_image': ['5', 0]}, 'class_type': 'KSampler', '_meta': {'title': 'KSampler'}}, '4': {'inputs': {'ckpt_name': 'darkSushiMixMix_brighterPruned.safetensors'}, 'class_type': 'CheckpointLoaderSimple', '_meta': {'title': 'Load Checkpoint'}}, '5': {'inputs': {'width': 512, 'height': 512, 'batch_size': 1}, 'class_type': 'EmptyLatentImage', '_meta': {'title': 'Empty Latent Image'}}, '6': {'inputs': {'text': 'masterpiece best quality man', 'clip': ['4', 1]}, 'class_type': 'CLIPTextEncode', '_meta': {'title': 'CLIP Text Encode (Prompt)'}}, '7': {'inputs': {'text': 'text, watermark', 'clip': ['4', 1]}, 'class_type': 'CLIPTextEncode', '_meta': {'title': 'CLIP Text Encode (Prompt)'}}, '8': {'inputs': {'samples': ['3', 0], 'vae': ['4', 2]}, 'class_type': 'VAEDecode', '_meta': {'title': 'VAE Decode'}}, '9': {'inputs': {'filename_prefix': 'ComfyUI', 'images': ['8', 0]}, 'class_type': 'SaveImage', '_meta': {'title': 'Save Image'}}}, {'client_id': 'd9150580-6a45-4bdf-92e0-3ae2105c9df1'}, ['9']], 'outputs': {'9': {'images': [{'filename': 'ComfyUI_01033_.png', 'subfolder': '', 'type': 'output'}]}}, 'status': {'status_str': 'success', 'completed': True, 'messages': [['execution_start', {'prompt_id': '79aa60c3-d8e1-4c3b-afa8-45067b0c0225'}], ['execution_cached', {'nodes': ['5', '3', '9', '4', '6', '8', '7'], 'prompt_id': '79aa60c3-d8e1-4c3b-afa8-45067b0c0225'}]]}}}

def get_images(ws, prompt): #入参是一个websocket连接 和 prompt(comfyui请求的api结构 json)
    response=queue_prompt(prompt)
    # print(response)
    prompt_id = response['prompt_id']
    
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing': #如果type是 executing,说明正在进行生图. 会一个节点一个节点的执行 
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id: #当node执行完了 最后一次值会是none
                    break #此时生成完成 {"type": "executing", "data": {"node": null, "prompt_id": "c4c469aa-d5ac-4088-a3f2-ad11e88630a7"}}
        else:
            continue #previews are binary data

    # history = get_history(prompt_id)
    # history = history[prompt_id]
   
    history = get_history(prompt_id)[prompt_id]
    # print(history)
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type']) #获取到comfyui把本次任务的结果存哪了
                    
                    images_output.append(image_data)
            output_images[node_id] = images_output #存储图片数据

    return output_images



# 在节点中通常包含多个参数，如果其中有些参数的值需要从其他节点获取，则这些参数的结构可以通过以下方式表达：参数的键是这个参数的名字,值是一个数组,数组的第一个值是传递这个参数值的来源节点序号 "n"，第二个值是来源节点中该参数值的顺序位置，从上往下从0开始计数。
prompt_text = """
{
  "1": {
    "inputs": {
      "seed": 2,
      "steps": 25,
      "cfg": 6,
      "sampler_name": "dpmpp_2m",
      "scheduler": "karras",
      "denoise": 1,
      "model": [
        "34",
        0
      ],
      "positive": [
        "4",
        0
      ],
      "negative": [
        "5",
        0
      ],
      "latent_image": [
        "3",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "2": {
    "inputs": {
      "ckpt_name": "majicmixRealistic_v7.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "3": {
    "inputs": {
      "width": 768,
      "height": 768,
      "batch_size": 4
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "4": {
    "inputs": {
      "text": "closeup illustration of a woman wearing a white spring dress in a garden,looking at viewer, high quality, diffuse light, highly detailed, 4k",
      "clip": [
        "33",
        0
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "5": {
    "inputs": {
      "text": "blurry, malformed, distorted, naked",
      "clip": [
        "33",
        0
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "6": {
    "inputs": {
      "samples": [
        "1",
        0
      ],
      "vae": [
        "7",
        0
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "7": {
    "inputs": {
      "vae_name": "kl-f8-anime2.ckpt"
    },
    "class_type": "VAELoader",
    "_meta": {
      "title": "Load VAE"
    }
  },
  "9": {
    "inputs": {
      "ipadapter_file": "IP-Adapter-FaceID/ip-adapter-faceid_sd15.bin"
    },
    "class_type": "IPAdapterModelLoader",
    "_meta": {
      "title": "Load IPAdapter Model"
    }
  },
  "14": {
    "inputs": {
      "lora_name": "faceid/ip-adapter-faceid_sd15_lora.safetensors",
      "strength_model": 0.6,
      "model": [
        "2",
        0
      ]
    },
    "class_type": "LoraLoaderModelOnly",
    "_meta": {
      "title": "LoraLoaderModelOnly"
    }
  },
  "22": {
    "inputs": {
      "images": [
        "6",
        0
      ]
    },
    "class_type": "PreviewImage",
    "_meta": {
      "title": "Preview Image"
    }
  },
  "31": {
    "inputs": {
      "clip_name": "clip-vit-h.safetensors"
    },
    "class_type": "CLIPVisionLoader",
    "_meta": {
      "title": "Load CLIP Vision"
    }
  },
  "32": {
    "inputs": {
      "provider": "CUDA"
    },
    "class_type": "InsightFaceLoader",
    "_meta": {
      "title": "Load InsightFace"
    }
  },
  "33": {
    "inputs": {
      "stop_at_clip_layer": -2,
      "clip": [
        "2",
        1
      ]
    },
    "class_type": "CLIPSetLastLayer",
    "_meta": {
      "title": "CLIP Set Last Layer"
    }
  },
  "34": {
    "inputs": {
      "lora_name": "sd15/rdjrock.safetensors",
      "strength_model": 0.8,
      "model": [
        "35",
        0
      ]
    },
    "class_type": "LoraLoaderModelOnly",
    "_meta": {
      "title": "LoraLoaderModelOnly"
    }
  },
  "35": {
    "inputs": {
      "weight": 1,
      "noise": 0,
      "weight_type": "original",
      "start_at": 0,
      "end_at": 1,
      "faceid_v2": false,
      "weight_v2": 1,
      "unfold_batch": false,
      "ipadapter": [
        "9",
        0
      ],
      "clip_vision": [
        "31",
        0
      ],
      "insightface": [
        "32",
        0
      ],
      "image": [
        "37",
        0
      ],
      "model": [
        "14",
        0
      ]
    },
    "class_type": "IPAdapterApplyFaceID",
    "_meta": {
      "title": "Apply IPAdapter FaceID"
    }
  },
  "37": {
    "inputs": {
      "urls": "https://awesomeaigc.oss-cn-hangzhou.aliyuncs.com/lena.jpeg"
    },
    "class_type": "LoadImageFromURL",
    "_meta": {
      "title": "Load Image From Url"
    }
  }
}
"""

prompt = json.loads(prompt_text)
#设置prompt
# prompt["6"]["inputs"]["text"] = "masterpiece best quality man"
#设置url
prompt["37"]["inputs"]["urls"] = "https://awesomeaigc.oss-cn-hangzhou.aliyuncs.com/%E6%9C%89%E7%88%B1%E5%8F%AF%E5%A5%88.jpg"
#设置种子数
# prompt["3"]["inputs"]["seed"] = 5

ws = websocket.WebSocket()
ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
images = get_images(ws, prompt)

#Commented out code to display the output images:

for node_id in images:
    for image_data in images[node_id]:
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(image_data))  #pillow库解析内存里的图片数据
        # draw = ImageDraw.Draw(image)
        # width, height = image.size
        # for x in range(0, width, 10):
        #     draw.line([(x, 0), (x, height)], fill='red')  # 竖直线
        # for y in range(0, height, 10):
        #     draw.line([(0, y), (width, y)], fill='red')  # 水平线
        image.show() #显示

