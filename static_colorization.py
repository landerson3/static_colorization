# accept a CSV of the SQL static colorization in the format of (FILE_NAME, SUFFIX, COLORIZATION_FILE_NAME, SWATCH_ID)
import sys, ftplib, requests, io, time, json, logging, threading
from PIL import Image

csv_file = sys.argv[1] if len(sys.argv)>1 else '/Users/landerson2/Desktop/colorlcolr.csv'
ALLOW_OVERWRITE = True
WIDTH = 4000
MAX_LONG_SIDE = 4000
URL_EXTENSION = '&fmt=png-alpha&qlt=100,1&op_sharpen=0&resMode=sharp2&op_usm=0,0,0,0&iccEmbed=0&printRes=72&bfc=off'


def download(file):
	try:
		response = requests.get(f'https://media.restorationhardware.com/is/image/rhis/{file}?req=imageprops,json')
		if response.status_code > 300:
			logging.warning(f"{response.status_code} received for {file}")
			return
		data_json = response.text.split("(", 1)[1].strip(")").strip(",\"\");")
		data_dict = json.loads(data_json)
		height = (data_dict['image.height'])
		width = (data_dict['image.width'])
		#print(width,height)

		if int(width) > 4000:
			height = round(int(height) * (4000/int(width)))
			width = 4000
			#print(width,height)
		
		if int(height) > 3125:
			width = round(int(width) * (3125/int(height)))
			height = 3125
			#print(width,height)

		

		download_url = f'https://media.restorationhardware.com/is/image/rhis/{file}?wid={width}&hei={height}&fmt=png-alpha'
		image_data = requests.get(download_url)
		im = Image.open(io.BytesIO(image_data.content))

		return im
		# im.save(f'{destination}{file}_RHR.png')
	except KeyError as err:
		logging.error(f"Key error {err} encountered for file: {file}")
		return None


def upload_to_ftp(binary, name):
	server = "s7ftp1.scene7.com"
	user_name = "rhis"
	password = "G1cO2@Me3N!"
	try:
		ftp = ftplib.FTP(host = server, user = user_name, passwd = password)
	except TimeoutError:
		time.sleep(15)
		ftp = ftplib.FTP(host = server, user = user_name, passwd = password)
	ftp.cwd('automated_uploads')
	binary.seek(0)
	try:
		ftp.storbinary(f"STOR {name}.png", fp = binary) ## TESTING ONLY
	except BrokenPipeError:
		upload_to_ftp(binary, name)
	return None


with open(csv_file) as csv:
	for _ in csv.readlines():
		prod_id, filename, suffix, colorization_file_name, swatch_id = _.replace('"',"").split(",")
		originating_name = None
		if filename != "" and suffix != "":
			originating_name = f'{filename}_{suffix}'
		else:
			originating_name = filename
		if originating_name == None: continue
		if 'FILE_NAME' in filename: continue
		if filename == None: continue
		swatch_id = swatch_id.replace("\n","")

		# process both RHR and non-RHR
		for i in range(2): # SWITCH TO TWO FOR LEGACY AND RHR
			# load the originating file
			rhr = bool(i)
			rhr = True ## RHR ONLY
			_rhr = '_RHR' if rhr else ''
			try:
				original_file = download(originating_name+_rhr)
			except:
				continue
			if original_file == None: 
				continue
			new_name = f"{colorization_file_name}{_rhr}_cl{swatch_id}"
			# print(new_name)
			# if response.content == bad_file or compare_files(originating_name, new_name, rhr): continue
			if ALLOW_OVERWRITE == False:
				# check if the new_name exists on the site and continue if it does
				response = requests.get(f'https://media.restorationhardware.com/is/image/rhis/{new_name}?req=exists,json')
				if '"catalogRecord.exists":"1"' in response.text:
					continue
			
			output = io.BytesIO()
			original_file.save(output, format = "PNG")
			while threading.active_count() > 15: continue
			threading.Thread(target = upload_to_ftp, args = (output, new_name)).start()
			