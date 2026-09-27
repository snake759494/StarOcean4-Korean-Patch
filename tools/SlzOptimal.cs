using System;
using System.IO;
using System.Collections.Generic;

// The same minimum-token v3 parser as slzenc.py, with bounded 4,095-word history.
public static class SlzOptimal {
    static byte[] Chunk(byte[] src,int offset,int size) {
        int n=size/2;
        ushort[] w=new ushort[n];
        for(int i=0;i<n;i++)w[i]=(ushort)(src[offset+2*i]|(src[offset+2*i+1]<<8));
        int[] lengths=new int[n],distances=new int[n];
        var history=new Dictionary<uint,List<int>>();
        for(int i=0;i<n-1;i++) {
            uint key=((uint)w[i]<<16)|w[i+1]; List<int> chain;
            int limit=Math.Min(17,n-i);
            if(history.TryGetValue(key,out chain)) {
                for(int j=chain.Count-1;j>=0;j--) {
                    int candidate=chain[j]; if(i-candidate>4095)break;
                    int length=2;
                    while(length<limit&&w[candidate+length]==w[i+length])length++;
                    if(length>lengths[i]) {lengths[i]=length;distances[i]=i-candidate;}
                    if(length==limit)break;
                }
            } else {chain=new List<int>();history[key]=chain;}
            chain.Add(i);
        }
        int[] cost=new int[n+1],take=new int[n];
        for(int i=n-1;i>=0;i--) {
            cost[i]=1+cost[i+1];take[i]=1;
            for(int length=2;length<=lengths[i];length++) {
                int value=1+cost[i+length];
                if(value<=cost[i]) {cost[i]=value;take[i]=length;}
            }
        }
        using(var memory=new MemoryStream())using(var writer=new BinaryWriter(memory)) {
            var tokens=new List<ushort>();int flags=0,bits=0;
            for(int i=0;i<n;) {
                int length=take[i];
                if(length==1) {flags|=1<<bits;tokens.Add(w[i]);}
                else tokens.Add((ushort)(distances[i]|((length-2)<<12)));
                i+=length;bits++;
                if(bits==16) {writer.Write((ushort)flags);foreach(ushort t in tokens)writer.Write(t);tokens.Clear();bits=0;flags=0;}
            }
            tokens.Add(0); // Mandatory native zero-distance terminator.
            writer.Write((ushort)flags);foreach(ushort t in tokens)writer.Write(t);
            return memory.ToArray();
        }
    }
    public static void Main(string[] args) {
        if(args.Length!=3)throw new ArgumentException("input decoded file, template SLZ, output SLZ required");
        byte[] data=File.ReadAllBytes(args[0]),template=File.ReadAllBytes(args[1]);
        if(template.Length<32||template[0]!=83||template[1]!=76||template[2]!=90)throw new InvalidDataException("SLZ template required");
        using(var memory=new MemoryStream())using(var writer=new BinaryWriter(memory)) {
            writer.Write(template,0,32);
            for(int offset=0;offset<data.Length;offset+=65536) {
                int size=Math.Min(65536,data.Length-offset);
                byte[] compressed=(size%2==0)?Chunk(data,offset,size):null;
                if(compressed==null||compressed.Length>=size) {writer.Write((ushort)(size&65535));writer.Write(data,offset,size);}
                else {writer.Write((ushort)compressed.Length);writer.Write(compressed);}
            }
            byte[] result=memory.ToArray();result[3]=3;result[25]=64;
            Array.Copy(BitConverter.GetBytes(result.Length-32),0,result,8,4);
            Array.Copy(BitConverter.GetBytes(data.Length),0,result,12,4);
            Array.Copy(BitConverter.GetBytes(32),0,result,20,4);
            File.WriteAllBytes(args[2],result);
            Console.WriteLine("Optimal SLZ: {0:N0} -> {1:N0}",data.Length,result.Length);
        }
    }
}
