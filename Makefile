
######################################
# Community identification workflow  #
######################################

# Put OSRM graph data into igraph format
%.igraph.pkl.gz: %.osrm
	./osrm2igraph.py $< $@

# Cluster nodes in graph using fast-greedy
%.communities.gz: %.igraph.pkl.gz find-communities.py 
	./find-communities.py --clusters 250 $< $@

# Smooth clustering using nearest neighbors
%.smoothed.communities.gz: %.communities.gz nearest-neighbors.py
	./nearest-neighbors.py $< $@ -k 30 

# Compute the concave hull for each community, and remove outlying islands
%.communities.hulls.json: %.smoothed.communities.gz concave-hulls.py
	./concave-hulls.py $< $@ --alphacut 10 --threads 4

# Delete communities which are spiky or "plus-sign" like.
%.communities.smooth.hulls.json: %.smoothed.communities.hulls.json clean-spiky-hulls.py
	./clean-spiky-hulls.py $< $@  --convexity 0.4

# Orphan nodes that don't lie very near their community hull.
%.communities.no-outliers.gz: %.smoothed.communities.gz %.communities.smooth.hulls.json clean-outliers.py
	./clean-outliers.py $< $*.communities.smooth.hulls.json $@ --buffer 0.05 --threads 4

# Clean up clustering to remove artifacts
%.communities.cleaned.gz: %.smoothed.communities.gz clean-communities.py
	./clean-communities.py $< $@ \
	  --alphacut 10 --buffer 0.03 --convexity 0.2 \
	  --min-tail-pinch 0.1 --max-tail-length 5 
	  #--bbox -11800000 3320000 -11880000 3392000 


# Make geo-json 
%.tesselation.json: %.communities.cleaned.gz tesselate-communities.py gis_data/ne_10m_urban_areas.shp gis_data/ne_10m_land.shp
	./tesselate-communities.py $< $@ --draw $*.pdf --AND gis_data/ne_10m_urban_areas.shp gis_data/ne_10m_land.shp

%.topo.json: %.tesselation.json
	./node_modules/topojson/bin/topojson -o $@ $< -s 5 -q 5000

all: los-angeles.igraph.pkl.gz los-angeles.communities.gz \
  los-angeles.communities.cleaned.gz \
  los-angeles.tesselation.json \
  los-angeles.topo.json

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
