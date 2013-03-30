
######################################
# Community identification workflow  #
######################################

# Put OSRM graph data into igraph format
%.igraph.pkl.gz: %.osrm
	./osrm2igraph.py $@ $<

# Cluster nodes in graph using fast-greedy
%.communities.gz: %.igraph.pkl.gz
	./communities.py --clusters 500 $< $@

# Make geo-json 
%.tesselation.json: 
	./voronoi.py 

######################################
# Downloading data 
######################################

# Land polygons
gis_data/ne_10m_land.zip: 
	mkdir -p gis_data
	cd gis_data && wget http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/physical/ne_10m_land.zip

gis_data/ne_10m_land.shp: gis_data/ne_10m_land.zip
	cd gis_data && unzip `basename $<`

# Urban areas
gis_data/ne_10m_urban_areas.zip:
	mkdir -p gis_data
	cd gis_data && wget http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_urban_areas.zip

gis_data/ne_10m_urban_areas.shp: gis_data/ne_10m_urban_areas.zip
	cd gis_data && unzip `basename $<`
