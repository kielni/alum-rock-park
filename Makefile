lint:
	npx prettier *.html --write
	npx prettier *.js --write
	npx prettier *.css --write


sync:
	# prereqs
	#   - set S3_BUCKET in environment
	#   - create config_aws.js with values for MAP_TILER_API_KEY and HOST on AWS
	echo "syncing to $(S3_BUCKET)"
	aws s3 cp index.html s3://$(S3_BUCKET)/arp/index.html --acl public-read
	aws s3 cp style.css s3://$(S3_BUCKET)/arp/style.css --acl public-read
	aws s3 cp map.js s3://$(S3_BUCKET)/arp/map.js --acl public-read
	aws s3 cp ARP_areas.geojson s3://$(S3_BUCKET)/arp/ARP_areas.geojson  --acl public-read
	aws s3 cp config_aws.js s3://$(S3_BUCKET)/arp/config.js  --acl public-read
	echo "http://$(S3_BUCKET).s3.us-west-2.amazonaws.com/arp/index.html"
