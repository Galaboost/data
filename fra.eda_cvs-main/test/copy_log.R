flist <- list.files("patha", "^filea.+[.]csv$", full.names = TRUE)
file.copy(flist, "pathb")


# create a timestamp   
str_time <- as.character(Sys.time())
str_time <- stringr::str_replace_all (str_time, "-","") 
str_time <- stringr::str_replace_all (str_time, ":",".") 
str_time <- stringr::str_replace_all (str_time, " ","_") 



getwd()
str_source = paste0(getwd(),"/log/log.txt") 
str_copy = paste0(getwd(),"/log/log_",str_time ,".txt")
file.copy(from=str_source, to=str_copy)


?file.copy

