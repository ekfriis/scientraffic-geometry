
######################################
# Community identification workflow  #
######################################

# Put OSRM graph data into igraph format
%.igraph.pkl.gz: %.osrm
	./osrm2igraph.py $< $@

# Cluster nodes in graph using fast-greedy
%.communities.gz: %.igraph.pkl.gz find-communities.py 
	./find-communities.py --clusters 500 $< $@

# Make geo-json 
%.tesselation.json: %.communities.gz tesselate-communities.py gis_data/ne_10m_urban_areas.shp gis_data/ne_10m_land.shp
	./tesselate-communities.py $< $@ --draw $*.pdf --bbox -118.20000 33.84000 -118.40000 33.92000 --AND gis_data/ne_10m_urban_areas.shp gis_data/ne_10m_land.shp

all: los-angeles.igraph.pkl.gz los-angeles.communities.gz los-angeles.tesselation.json

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
