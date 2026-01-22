lint:
	npx prettier *.html --write
	npx prettier *.js --write
	npx prettier *.css --write


sync:
	# prereqs
	#   - set S3_BUCKET in environment
	#   - create config_aws.js with values for MAP_TILER_API_KEY and HOST on AWS
	echo "syncing to $(S3_BUCKET)"
	# aws s3 cp index.html s3://$(S3_BUCKET)/index.html
	# aws s3 cp bay.html s3://$(S3_BUCKET)/bay.html
	# aws s3 cp config_aws.js s3://$(S3_BUCKET)/config.js
	# aws s3 cp output/routes_gz.geojson s3://$(S3_BUCKET)/routes.geojson --content-encoding gzip --content-type application/json
	# aws s3 cp output/ridge_trail_gz.geojson s3://$(S3_BUCKET)/ridge_trail.geojson --content-encoding gzip --content-type application/json
	# aws s3 cp output/bay_trail_gz.geojson s3://$(S3_BUCKET)/bay_trail.geojson --content-encoding gzip --content-type application/json
	# aws s3 cp output/trail_routes_gz.geojson s3://$(S3_BUCKET)/trail_routes.geojson --content-encoding gzip --content-type application/json
	echo "http://$(S3_BUCKET).s3-website-us-east-1.amazonaws.com/index.html"
