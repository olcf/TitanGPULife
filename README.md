# titan-gpu

- Paper about Titan GPU reliability analysis.
- Includes R code to generate graphics and more analysis.
  - See code/README for instructions
- Includes original Titan reliability data
  - data/titan.gpu.history.txt - history data
  - data/titan.service.txt - service nodes for exclusion
- Includes output data files produced by code/TitanGPUmodel.Rmd
  - data/gc_full.csv - cleaned up data (see paper and R code)
  - data/gc_summary_loc.csv - one record per GPU (variables: SN,time,nlife,nloc,last,col,row,cage,slot,node,max_loc_events,time_max_loc,dbe,dbe_loc,otb,otb_loc,out,batch,days,years,dead,dead_otb,dead_dbe) (see paper and R code)
- Includes .Rmd analysis document as TitanGPUmode.html