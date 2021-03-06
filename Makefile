
# Output target template
OUTPUT=CITY/igraph.pkl.gz\
       CITY/communities.gz\
       CITY/communities.smoothed.gz\
       CITY/communities.hulls.json\
       CITY/communities.smooth.hulls.json\
       CITY/communities.no-tails.json\
       CITY/communities.no-outliers.gz\
       CITY/communities.associate-outliers.gz\
       CITY/communities.edges.gz\
       CITY/tesselation.json\
       CITY/topo.json

LA_TARGETS=$(subst CITY,los-angeles,$(OUTPUT))

la: $(LA_TARGETS)

######################################
# Community identification workflow  #
######################################

# Put OSRM graph data into igraph format
%/igraph.pkl.gz: %/osrm
	./osrm2igraph.py $< $@

# Cluster nodes in graph using fast-greedy
%/communities.gz: %/igraph.pkl.gz find-communities.py 
	./find-communities.py --clusters 0 $< $@

# Smooth clustering using nearest neighbors
%/communities.smoothed.gz: %/communities.gz nearest-neighbors.py
	./nearest-neighbors.py $< $@ -k 30 

# Compute the concave hull for each community, and remove outlying islands
%/communities.hulls.json: %/communities.smoothed.gz concave-hulls.py
	./concave-hulls.py $< $@ --alphacut 10 --threads 4

# Delete communities which are spiky or "plus-sign" like.
%/communities.smooth.hulls.json: %/communities.hulls.json clean-spiky-hulls.py
	./clean-spiky-hulls.py $< $@  --convexity 0.4

# Remove tails from communities
%/communities.no-tails.json: %/communities.smooth.hulls.json trim-tails.py
	./trim-tails.py $< $@ --min-tail-pinch 0.05 --max-tail-length 10

# Orphan nodes that don't lie very near their community hull.
%/communities.no-outliers.gz: %/communities.smoothed.gz %/communities.no-tails.json clean-outliers.py
	./clean-outliers.py $< $*/communities.no-tails.json $@ --buffer 0.05 --threads 4

# Reassociate all orphans with their neighbors
%/communities.associate-outliers.gz: %/communities.no-outliers.gz
	./nearest-neighbors.py $< $@ -k 30 --only-orphans

# Get only the nodes on the edges of the communities, so the tesselation isn't
# slow.
%/communities.edges.gz: %/communities.associate-outliers.gz %/communities.smooth.hulls.json
	./find-edge-nodes.py $< $*/communities.smooth.hulls.json $@ --within 0.07 --keep 0.03 --threads 4

# Make voronoi geo-json 
%/tesselation.json: %/communities.edges.gz tesselate-communities.py gis_data/ne_10m_urban_areas.shp gis_data/ne_10m_land.shp
	./tesselate-communities.py $< $@ --draw $*/tesselation.pdf --AND gis_data/ne_10m_urban_areas.shp gis_data/ne_10m_land.shp

# Merge all the puny communities into big ones
%/tesselation.merged.json: %/tesselation.json merge-tiny-communities.py
	./merge-tiny-communities.py $< $@ --min-wrt-quantile50 0.25

#%/topo.json: %/tesselation.json
%/topo.json: %/tesselation.merged.json
	./node_modules/topojson/bin/topojson -o $@ $< -q 1e3 -s 1E-9

######################################
# Downloading data 
######################################

# Land polygons
gis_data/ne_10m_land.zip: 
	mkdir -p gis_data
	cd gis_data && wget http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/physical/ne_10m_land.zip

gis_data/ne_10m_land.shp: gis_data/ne_10m_land.zip
	cd gis_data && unzip `basename $<`
	touch $@

# Urban areas
gis_data/ne_10m_urban_areas.zip:
	mkdir -p gis_data
	cd gis_data && wget http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_urban_areas.zip

gis_data/ne_10m_urban_areas.shp: gis_data/ne_10m_urban_areas.zip
	cd gis_data && unzip `basename $<`
	touch $@
