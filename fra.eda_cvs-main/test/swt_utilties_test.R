
dt_results <- data.frame( 
  id  = character() , 
  function_name = character(), 
  status = factor(),
  speed_record = double()
  )

add_to_result <- function(id,function_name,status, speed, dt_results ){
  dt <- data.frame(
    id  = id , 
    function_name = function_name ,
    status = status , 
    speed_record = speed
  )
  
  dt_results <- rbind(dt_results, dt) 
  return(dt_results)
}



# Chap0 ---------------------------------------------------
#..sql_dmp ----
id ="0.2"
function_name = "sql_dmp"

e1 = Sys.time()
  df <- sql_dmp("SELECT * from t_dcs_info ", conid = conid)
e2=Sys.time()
speed = e2 - e1 

if (nrow(df) > 1){status ="PASS"} else{ status = "FAIL"} 

dt_results <- add_to_result(
  id=id,function_name=function_name, 
  status=status, speed=speed, 
  dt_results=dt_results )


 
# Chap1---------------------------------------------------
# 1.1 get_swt_profiles ----
id ="1.1"
function_name = "get_swt_profiles  "

e1 = Sys.time()
df <- get_swt_profiles( conid = conid)
e2=Sys.time()
speed = e2 - e1 

if (nrow(df) > 1){status ="PASS"} else{ status = "FAIL"} 

dt_results <- add_to_result(
    id=id,function_name=function_name, 
    status=status, speed=speed, 
    dt_results=dt_results )
  

# 1.2 get_address ----
id ="1.2"
function_name = "get_address"

# 1.2.1 missing techno 
e1 = Sys.time()
df <- get_address(str_techno="C12", str_root= root_address)
e2=Sys.time()
speed = e2 - e1 

if (substr(df,1,3) !="Err"  ){status ="PASS"} else{ status = "FAIL"} 

dt_results <- add_to_result(
  id=id,function_name=function_name, 
  status=status, speed=speed, 
  dt_results=dt_results )



# 1.2.1 defined  techno 
e1 = Sys.time()
df <- get_address(str_techno="XH018", str_root= root_address)
e2=Sys.time()
speed = e2 - e1 

if (substr(df,1,3) !="Err"  ){status ="PASS"} else{ status = "FAIL"} 

dt_results <- add_to_result(  id=id,function_name=function_name,   status=status, speed=speed, dt_results=dt_results )

#1.3.  get_pmax ----
id ="1.3"
function_name = "get_pmax"

# 1.3.1 existing tech != T18SO  
e1 = Sys.time()
res <- get_pmax(str_techno="C11")
e2=Sys.time()
speed =   e2 - e1  

if ( res = "12000" ){status ="PASS"} else{ status = "FAIL"} 
dt_results <- add_to_result(  id=id,function_name=function_name,   status=status, speed=speed, dt_results=dt_results )

# 1.3.2 existing tech  = T18SO  
e1 = Sys.time()
res <- get_pmax(str_techno="T18SO")
e2=Sys.time()
speed = e2 - e1 


if (  es =="10000"){status ="PASS"} else{ status = "FAIL"} 
dt_results <- add_to_result(  id=id,function_name=function_name,   status=status, speed=speed, dt_results=dt_results )


#1.4.  get_nparam ----
id ="1.4"
function_name = "get_nparam"

# 1.4.1 with predifine list   
e1 = Sys.time()
res <- get_nparam(str_techno="XH018")
e2=Sys.time()
speed =   e2 - e1  


if ( res != "none" ){status ="PASS"} else{ status = "FAIL"} 
dt_results <- add_to_result(  id=id,function_name=function_name,   status=status, speed=speed, dt_results=dt_results )


# 1.4.1 without predifine list   
e1 = Sys.time()
res <- get_nparam(str_techno="T18SO")
e2=Sys.time()
speed =   e2 - e1  


if ( res != "none" ){status ="PASS"} else{ status = "FAIL"} 
dt_results <- add_to_result(  id=id,function_name=function_name,   status=status, speed=speed, dt_results=dt_results )


# no nparam test 
str_nparam <- f_param_list(fstr_npnpid = "0010", fstr_version = "30", conid=conid)

# Chap2 ---- 
#2.1 f_update_data_lot----
id ="2.1"
function_name = "f_update_data_lot "

xstr_address = "~/share/PROD_EDA_PUBLIC/CARAC/FWT_T18RF"
xstr_npnpid ="7722"
xstr_version="1"
xstr_pmax ="12000"
xstr_nparam=paste0("10691,10692,10693,10595,10596,10597,10598,10599,10000",
                   "10001,10002,10003,10004,10005,10006,10007,10008,10009,10015,10017,",
                   "10026,10027,10028,10029,10030,10037,10063,10064,10072,10074,10080,10327"  )

xstr_date1 = paste0("'",as.character(today() - months(3) ),"'")
xstr_date2 = paste0("'",as.character(today()),"'")


e1 = Sys.time()
df <- f_update_data_lot( xstr_address, xstr_npnpid, xstr_version , xstr_nparam, xstr_pmax, xstr_date1 ,xstr_date2 )
e2=Sys.time()
speed = e2 - e1 

if (nrow(df) > 1){status ="PASS"} else{ status = "FAIL"} 
dt_results <- add_to_result(
  id=id,function_name=function_name, 
  status=status, speed=speed, 
  dt_results=dt_results )

# 2.2 f_update_data_wafer ----
id ="2.2"
function_name = "f_update_data_wafer "

xstr_address = "~/share/PROD_EDA_PUBLIC/CARAC/FWT_T18RF"
xstr_npnpid ="7722"
xstr_version="1"
xstr_pmax ="12000"
xstr_nparam=paste0("10691,10692,10693,10595,10596,10597,10598,10599,10000",
                   "10001,10002,10003,10004,10005,10006,10007,10008,10009,10015,10017,",
                   "10026,10027,10028,10029,10030,10037,10063,10064,10072,10074,10080,10327"  )

xstr_date1 = paste0("'",as.character(today() - months(3) ),"'")
xstr_date2 = paste0("'",as.character(today()),"'")




e1 = Sys.time()
df <- f_update_data_lot( xstr_address, xstr_npnpid, xstr_version , xstr_nparam, xstr_pmax, xstr_date1 ,xstr_date2 )
e2=Sys.time()
speed = e2 - e1 

if (nrow(df) > 1){status ="PASS"} else{ status = "FAIL"} 
dt_results <- add_to_result(
  id=id,function_name=function_name, 
  status=status, speed=speed, 
  dt_results=dt_results )

# ------------------------- THE END  --------------------------------------
#--------------------------------------------------------------------------#
#--------------------------------------------------------------------------#
#--------------------------------------------------------------------------#



# # for debug
# list_waf = f_update_data_wafer( xstr_address, xstr_npnpid, xstr_version , xstr_nparam, xstr_pmax, xstr_date1 ,xstr_date2 )
# df1 = list_waf[[1]]
# df2 = list_waf[[2]]
# df3 = list_waf[[3]]