.PHONY: lint lint-py gallery sync sync-photos .prep

# local.env's `export KEY=value` lines are also valid Make syntax; export
# (no args) re-exports everything from it to every recipe's subshell, so
# individual targets don't need a `. ./local.env &&` prefix.
include local.env
export

lint:
	npx prettier *.html --write
	npx prettier *.js --write
	npx prettier *.css --write


lint-py:
	uv run black claude.py preprocess.py
	uv run flake8 preprocess.py --max-line-length=88


prep:
	# get Ente photos (may be from others)
	ente export --albums "Alum Rock Park"
	# overwrite with Photos version (may have additional metadata)
	uv run osxphotos export $(PHOTOS_DIR) \
		--album "Alum Rock Park" \
		--exiftool \
		--update \
		--download-missing

gallery: prep
	# prereqs: set PHOTOS_DIR and PROJECT_DIR in local.env
	uv run python preprocess.py


sync:
	# prereqs: cconfig_aws.js with values for MAP_TILER_API_KEY and HOST on AWS
	echo "syncing web/ to $(S3_BUCKET)/arp"
	aws s3 cp web/index.html s3://$(S3_BUCKET)/arp/index.html --acl public-read
	aws s3 cp web/map.html s3://$(S3_BUCKET)/arp/map.html --acl public-read
	aws s3 cp web/style.css s3://$(S3_BUCKET)/arp/style.css --acl public-read
	aws s3 cp web/map.js s3://$(S3_BUCKET)/arp/map.js --acl public-read
	aws s3 cp web/gallery.js s3://$(S3_BUCKET)/arp/gallery.js --acl public-read
	aws s3 cp web/ARP_areas.geojson s3://$(S3_BUCKET)/arp/ARP_areas.geojson  --acl public-read
	aws s3 cp web/config_aws.js s3://$(S3_BUCKET)/arp/config.js  --acl public-read
	echo "http://$(S3_BUCKET).s3.us-west-2.amazonaws.com/arp/index.html"


sync-photos: gallery
	echo "syncing web/photos/ to $(S3_BUCKET)"
	aws s3 sync web/photos s3://$(S3_BUCKET)/arp/photos --acl public-read
	aws s3 cp web/photos.json s3://$(S3_BUCKET)/arp/photos.json --acl public-read
