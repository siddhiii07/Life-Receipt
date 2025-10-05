import express from 'express';
import bodyParser from 'body-parser';
import { dirname} from 'path';
import { fileURLToPath } from 'url'; 

const _dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = 3000;

app.use(bodyParser.urlencoded({extended:true}));
app.use(express.static(_dirname + '/public'));


app.get('/',(req, res)=>{
    res.sendFile(_dirname + '/public/index.html')
});

app.get('/login',(req, res)=>{
    res.sendFile(_dirname + '/public/login.html')
});

app.get('/signup',(req, res)=>{
    res.sendFile(_dirname + '/public/signup.html')
});

app.get('/data',(req, res)=>{
    res.sendFile(_dirname + '/public/data.html')
});

app.listen(PORT , ()=>{
    console.log("Server is running on port " + PORT)
});
